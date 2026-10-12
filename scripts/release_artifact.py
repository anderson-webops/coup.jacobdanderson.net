"""Build and verify a source-bound, immutable Coup static release."""

from __future__ import annotations

import argparse
import gzip
from hashlib import sha256
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = 1
APPLICATION_ID = "coup.jacobdanderson.net"
MANIFEST_NAME = "release-manifest.json"
CHECKSUM_NAME = "SHA256SUMS"
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_CONTROL_BYTES = 256 * 1024


class ReleaseError(ValueError):
    """An artifact failed the Coup source or publication contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseError(message)


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(128 * 1024):
            value.update(chunk)
    return value.hexdigest()


def read_regular(path: Path, maximum: int) -> bytes:
    require(not path.is_symlink() and path.is_file(), f"Missing or linked file: {path}")
    require(path.stat().st_size <= maximum, f"File exceeds size limit: {path}")
    raw = path.read_bytes()
    require(len(raw) <= maximum, f"File exceeds size limit: {path}")
    return raw


def _unique_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path) -> tuple[bytes, dict]:
    raw = read_regular(path, MAX_CONTROL_BYTES)
    value = json.loads(raw, object_pairs_hook=_unique_keys)
    require(isinstance(value, dict), f"JSON object required: {path}")
    return raw, value


def git_output(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.strip()


def source_identity(root: Path, require_clean: bool) -> tuple[str, bool]:
    commit = git_output(root, "rev-parse", "HEAD")
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "Invalid source commit")
    clean = not git_output(root, "status", "--porcelain", "--untracked-files=all")
    require(clean or not require_clean, "Release artifacts require a clean checkout")
    return commit, clean


def run_site_checker(root: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(ROOT / "check_site.py"), "--root", str(root)],
        check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    require(result.returncode == 0, f"Coup publication check failed: {(result.stderr or result.stdout).strip()[:2000]}")


def validate_contract(contract: dict) -> None:
    require(contract.get("schema_version") == SCHEMA_VERSION, "Unsupported deployment contract")
    require(contract.get("application_id") == APPLICATION_ID, "Wrong application identity")
    require(contract.get("domain") == APPLICATION_ID, "Wrong deployment domain")
    require(contract.get("artifact_format") == "coup-static-dist-tar-v1", "Wrong artifact format")
    require(contract.get("public_root") == "dist", "Only dist may be public")
    runtime = contract.get("runtime")
    require(isinstance(runtime, dict), "Runtime contract missing")
    require(runtime.get("kind") == "static-files" and runtime.get("site_process") is False,
            "A site process is not part of this release")
    require(runtime.get("writable_state") is False, "Static release must have no writable state")
    require(runtime.get("operating_system") == "linux" and runtime.get("architecture") == "any",
            "Unsupported static host platform")
    capabilities = contract.get("minimum_host_capabilities")
    require(isinstance(capabilities, list) and len(capabilities) >= 4
            and all(isinstance(item, str) and item for item in capabilities)
            and len(set(capabilities)) == len(capabilities), "Invalid host capabilities")
    require(contract.get("response_policy_file") == "security/site-policy.json",
            "Response policy must be a separate reviewed control")
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "Readiness contract missing")
    require(set(readiness.get("address_families", [])) == {"ipv4", "ipv6"}
            and readiness.get("scheme") == "https", "Both address families and HTTPS are required")
    require(readiness.get("identity_path") == "/"
            and readiness.get("identity_file") == "dist/index.html"
            and readiness.get("identity_sha256_from") == "release-manifest.json.files"
            and readiness.get("asset_sha256_from") == "release-manifest.json.files",
            "Readiness must verify exact published bytes")
    require(readiness.get("missing_path") == "/__coup_release_probe_missing__"
            and readiness.get("missing_status") == 404, "Real 404 readiness probe required")
    require(readiness.get("required_headers_from") == "release-manifest.json.site_policy",
            "Readiness must verify the reviewed response policy")
    require(contract.get("migrations") == {"required": False}, "Static release cannot require migrations")
    rollback = contract.get("rollback")
    require(isinstance(rollback, dict) and rollback.get("required") is True
            and rollback.get("mode") == "immutable-retained-prior-release-when-present"
            and rollback.get("first_activation_failure") == "restore-prior-absent-state"
            and rollback.get("retain_after_first_activation") is True
            and rollback.get("verification") == "prior-manifest-and-readiness-when-present",
            "First activation and immutable retained rollback must be defined")


def _public_files(dist: Path) -> set[str]:
    require(dist.is_dir() and not dist.is_symlink(), "Static dist directory is missing or linked")
    found: set[str] = set()

    def visit(directory: Path) -> None:
        for path in directory.iterdir():
            require(not path.is_symlink(), f"Linked publication path: {path}")
            if path.is_dir():
                visit(path)
            else:
                require(path.is_file(), f"Unsupported publication path: {path}")
                found.add(path.relative_to(dist).as_posix())

    visit(dist)
    return found


def publication_records(root: Path, anchor: dict) -> list[dict]:
    approved = anchor.get("publication_files")
    require(isinstance(approved, dict) and approved, "Publication anchor needs a file inventory")
    require(set(approved) == _public_files(root / "dist"), "Dist inventory differs from approved publication")
    records = []
    total = 0
    for name, record in sorted(approved.items()):
        posix = PurePosixPath(name)
        require(not posix.is_absolute() and name == posix.as_posix()
                and all(part not in ("", ".", "..") for part in posix.parts),
                f"Invalid publication path: {name}")
        require(isinstance(record, dict)
                and set(record) == {"media_type", "sha256", "size"},
                f"Invalid anchor record: {name}")
        require(isinstance(record["media_type"], str) and "/" in record["media_type"],
                f"Invalid media type: {name}")
        require(isinstance(record["size"], int) and not isinstance(record["size"], bool)
                and 0 <= record["size"] <= MAX_TOTAL_BYTES,
                f"Invalid approved size: {name}")
        require(isinstance(record["sha256"], str)
                and re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) is not None,
                f"Invalid approved digest: {name}")
        raw = read_regular(root / "dist" / name, MAX_TOTAL_BYTES)
        require(len(raw) == record["size"] and digest(raw) == record["sha256"],
                f"Publication changed after approval: {name}")
        total += len(raw)
        require(total <= MAX_TOTAL_BYTES, "Public tree exceeds size limit")
        records.append({"path": f"dist/{name}", "media_type": record["media_type"],
                        "sha256": record["sha256"], "size": record["size"]})
    require(any(row["path"] == "dist/index.html" for row in records), "Public homepage is required")
    return records


def source_controls(root: Path) -> tuple[str, bytes, dict, bytes, dict, bytes, dict, list[dict]]:
    version = read_regular(root / "VERSION", 64).decode("ascii").strip()
    require(re.fullmatch(r"\d+\.\d+\.\d+", version) is not None, "VERSION must be semantic")
    anchor_raw, anchor = read_json(root / "security" / "approved-publication.json")
    contract_raw, contract = read_json(root / "deployment-contract.json")
    policy_raw, policy = read_json(root / "security" / "site-policy.json")
    validate_contract(contract)
    source_hashes = anchor.get("research_source_sha256")
    require(isinstance(source_hashes, dict) and source_hashes
            and all(isinstance(name, str) and isinstance(value, str)
                    and re.fullmatch(r"[0-9a-f]{64}", value) is not None
                    for name, value in source_hashes.items()),
            "Publication anchor needs research source hashes")
    records = publication_records(root, anchor)
    return version, anchor_raw, anchor, contract_raw, contract, policy_raw, policy, records


def normalized_tar_info(name: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = 0o644
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def validate_output_directory(root: Path, output_dir: Path) -> None:
    """Allow external build paths or an exact ignored path under local .ai-work."""
    if not output_dir.is_relative_to(root):
        return
    relative = output_dir.relative_to(root)
    require(len(relative.parts) >= 2 and relative.parts[0] == ".ai-work",
            "In-repository release output must be inside ignored .ai-work")
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "-q", "--no-index", "--", str(output_dir)],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    require(result.returncode == 0, "Release output path is not Git-ignored")


def build_release(root: Path, output_dir: Path, *, source_commit: str | None = None,
                  source_clean: bool | None = None, require_clean: bool = True) -> dict:
    root = root.resolve()
    output_dir = output_dir.resolve()
    validate_output_directory(root, output_dir)
    run_site_checker(root)
    version, anchor_raw, anchor, contract_raw, contract, policy_raw, policy, records = source_controls(root)
    if source_commit is None or source_clean is None:
        source_commit, source_clean = source_identity(root, require_clean)
    require(re.fullmatch(r"[0-9a-f]{40}", source_commit) is not None, "Invalid source commit")
    require(source_clean or not require_clean, "Release artifacts require a clean checkout")
    output_dir.mkdir(parents=True, exist_ok=True)
    require(not any(output_dir.iterdir()), "Release output directory must be empty")

    archive_name = f"coup-site-v{version}-{source_commit[:12]}.tar.gz"
    archive_path = output_dir / archive_name
    with archive_path.open("wb") as destination:
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                for record in records:
                    raw = read_regular(root / record["path"], MAX_TOTAL_BYTES)
                    archive.addfile(normalized_tar_info(record["path"], len(raw)), io.BytesIO(raw))

    manifest = {
        "document_type": "coup.static-release",
        "schema_version": SCHEMA_VERSION,
        "application_id": APPLICATION_ID,
        "version": version,
        "source_commit": source_commit,
        "source_clean": bool(source_clean),
        "approved_publication_sha256": digest(anchor_raw),
        "research_source_sha256": anchor["research_source_sha256"],
        "deployment_contract_sha256": digest(contract_raw),
        "site_policy_sha256": digest(policy_raw),
        "deployment": contract,
        "site_policy": policy,
        "archive": {"name": archive_name, "sha256": file_digest(archive_path),
                    "size": archive_path.stat().st_size},
        "files": records,
    }
    manifest_path = output_dir / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    (output_dir / CHECKSUM_NAME).write_text(
        f"{manifest['archive']['sha256']}  {archive_name}\n"
        f"{file_digest(manifest_path)}  {MANIFEST_NAME}\n"
    )
    return manifest


def safe_archive_members(archive_path: Path, expected: dict[str, dict]) -> dict[str, bytes]:
    require(archive_path.stat().st_size <= MAX_TOTAL_BYTES, "Compressed archive exceeds size limit")
    extracted: dict[str, bytes] = {}
    total = 0
    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = archive.getmembers()
        require(len(members) == len(expected), "Archive inventory differs from release manifest")
        for member in members:
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and ".." not in path.parts
                    and member.name == path.as_posix() and path.parts[:1] == ("dist",),
                    f"Unsafe archive path: {member.name}")
            require(member.isfile() and not member.issym() and not member.islnk(),
                    f"Unsupported archive member: {member.name}")
            require(member.name in expected and member.name not in extracted,
                    f"Unexpected or duplicate archive member: {member.name}")
            require(member.size == expected[member.name]["size"],
                    f"Archive member size differs: {member.name}")
            total += member.size
            require(total <= MAX_TOTAL_BYTES, "Expanded archive exceeds size limit")
            stream = archive.extractfile(member)
            require(stream is not None, f"Unreadable archive member: {member.name}")
            raw = stream.read(member.size + 1)
            require(len(raw) == member.size and digest(raw) == expected[member.name]["sha256"],
                    f"Archive member digest differs: {member.name}")
            extracted[member.name] = raw
    require(set(extracted) == set(expected), "Archive is missing an approved file")
    return extracted


def verify_release(root: Path, release_dir: Path, *, expected_commit: str | None = None,
                   expected_version: str | None = None) -> dict:
    root = root.resolve()
    release_dir = release_dir.resolve()
    run_site_checker(root)
    version, anchor_raw, anchor, contract_raw, contract, policy_raw, policy, records = source_controls(root)
    manifest_raw, manifest = read_json(release_dir / MANIFEST_NAME)
    required = {
        "document_type", "schema_version", "application_id", "version", "source_commit",
        "source_clean", "approved_publication_sha256", "research_source_sha256",
        "deployment_contract_sha256",
        "site_policy_sha256", "deployment", "site_policy", "archive", "files",
    }
    require(set(manifest) == required, "Unexpected release manifest fields")
    require(manifest["document_type"] == "coup.static-release"
            and manifest["schema_version"] == SCHEMA_VERSION
            and manifest["application_id"] == APPLICATION_ID,
            "Wrong release identity or schema")
    require(manifest["version"] == version
            and re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"]) is not None,
            "Release version differs from source")
    require(manifest["source_clean"] is True, "Release source was not clean")
    require(isinstance(manifest["source_commit"], str)
            and re.fullmatch(r"[0-9a-f]{40}", manifest["source_commit"]) is not None,
            "Invalid release source commit")
    if expected_commit is not None:
        require(manifest["source_commit"] == expected_commit, "Release source differs from expected commit")
    if expected_version is not None:
        require(manifest["version"] == expected_version, "Release differs from expected version")
    require(manifest["approved_publication_sha256"] == digest(anchor_raw)
            and manifest["deployment_contract_sha256"] == digest(contract_raw)
            and manifest["site_policy_sha256"] == digest(policy_raw),
            "Release control hash differs from source")
    require(manifest["research_source_sha256"] == anchor["research_source_sha256"],
            "Release research source hashes differ from approval")
    require(manifest["deployment"] == contract and manifest["site_policy"] == policy,
            "Release policy or deployment contract differs from source")
    require(manifest["files"] == records, "Release file inventory differs from approval")

    archive = manifest["archive"]
    require(isinstance(archive, dict) and set(archive) == {"name", "sha256", "size"},
            "Invalid archive record")
    expected_name = f"coup-site-v{version}-{manifest['source_commit'][:12]}.tar.gz"
    require(archive["name"] == expected_name, "Archive name is not source-bound")
    archive_path = release_dir / expected_name
    require(not archive_path.is_symlink() and archive_path.is_file(), "Release archive is missing or linked")
    require(isinstance(archive["size"], int) and archive_path.stat().st_size == archive["size"],
            "Release archive size differs from manifest")
    require(file_digest(archive_path) == archive["sha256"], "Release archive digest differs from manifest")
    expected_checksums = (f"{archive['sha256']}  {expected_name}\n"
                          f"{digest(manifest_raw)}  {MANIFEST_NAME}\n")
    checksums = read_regular(release_dir / CHECKSUM_NAME, 4 * 1024).decode("ascii")
    require(checksums == expected_checksums, "SHA256SUMS differs from release manifest")

    expected_files = {record["path"]: record for record in records}
    extracted = safe_archive_members(archive_path, expected_files)
    with tempfile.TemporaryDirectory() as directory:
        extracted_root = Path(directory)
        for name, raw in extracted.items():
            target = extracted_root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        (extracted_root / "security").mkdir()
        (extracted_root / "security" / "approved-publication.json").write_bytes(anchor_raw)
        (extracted_root / "security" / "site-policy.json").write_bytes(policy_raw)
        (extracted_root / "deployment-contract.json").write_bytes(contract_raw)
        run_site_checker(extracted_root)
    return manifest


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build").add_argument("--output-dir", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--release-dir", type=Path, required=True)
    verify.add_argument("--expected-commit")
    verify.add_argument("--expected-version")
    return parser


def main() -> int:
    args = argument_parser().parse_args()
    try:
        if args.command == "build":
            manifest = build_release(ROOT, args.output_dir)
            print(f"PASS: built {manifest['archive']['name']} from {manifest['source_commit']}.")
        else:
            manifest = verify_release(ROOT, args.release_dir,
                                      expected_commit=args.expected_commit,
                                      expected_version=args.expected_version)
            print(f"PASS: verified {manifest['archive']['name']} and isolated static tree.")
    except (OSError, UnicodeError, json.JSONDecodeError, subprocess.CalledProcessError,
            tarfile.TarError, ReleaseError, TypeError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
