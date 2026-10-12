"""Integrity tests for the immutable Coup static release."""

from __future__ import annotations

from hashlib import sha256
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

from scripts.release_artifact import (
    ROOT, ReleaseError, build_release, validate_output_directory, verify_release,
)


COMMIT = "a" * 40


class ReleaseArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = os.environ.get("RUNNER_TEMP")
        if scratch is None and (ROOT / ".ai-work" / "runs").is_dir():
            scratch = str(ROOT / ".ai-work" / "runs")
        self.temporary = tempfile.TemporaryDirectory(prefix="coup-release-test-", dir=scratch)
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.source = base / "source"
        self.release = base / "release"
        self.source.mkdir()
        shutil.copytree(ROOT / "dist", self.source / "dist")
        shutil.copytree(ROOT / "security", self.source / "security")
        shutil.copy2(ROOT / "deployment-contract.json", self.source / "deployment-contract.json")
        shutil.copy2(ROOT / "VERSION", self.source / "VERSION")
        self.manifest = build_release(
            self.source, self.release, source_commit=COMMIT,
            source_clean=True, require_clean=False,
        )

    @property
    def archive_path(self) -> Path:
        return self.release / self.manifest["archive"]["name"]

    @property
    def manifest_path(self) -> Path:
        return self.release / "release-manifest.json"

    def rewrite_manifest_and_checksums(self, manifest: dict) -> None:
        self.manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
        (self.release / "SHA256SUMS").write_text(
            f"{sha256(self.archive_path.read_bytes()).hexdigest()}  {self.archive_path.name}\n"
            f"{sha256(self.manifest_path.read_bytes()).hexdigest()}  release-manifest.json\n"
        )
        self.manifest = manifest

    def repack(self, *, replacement: str | None = None, kind: str = "file",
               duplicate: bool = False) -> None:
        malicious = self.release / "replacement.tar.gz"
        first = self.manifest["files"][0]["path"]
        with tarfile.open(malicious, "w:gz") as archive:
            for record in self.manifest["files"]:
                name = replacement if record["path"] == first and replacement else record["path"]
                member = tarfile.TarInfo(name)
                if record["path"] == first and kind == "symlink":
                    member.type = tarfile.SYMTYPE
                    member.linkname = "/etc/passwd"
                    archive.addfile(member)
                else:
                    raw = (self.source / record["path"]).read_bytes()
                    member.size = len(raw)
                    archive.addfile(member, io.BytesIO(raw))
            if duplicate:
                raw = (self.source / first).read_bytes()
                member = tarfile.TarInfo(first)
                member.size = len(raw)
                archive.addfile(member, io.BytesIO(raw))
        malicious.replace(self.archive_path)
        updated = json.loads(self.manifest_path.read_text())
        updated["archive"]["sha256"] = sha256(self.archive_path.read_bytes()).hexdigest()
        updated["archive"]["size"] = self.archive_path.stat().st_size
        self.rewrite_manifest_and_checksums(updated)

    def test_exact_release_roundtrip_and_public_only_archive(self) -> None:
        checked = verify_release(self.source, self.release,
                                 expected_commit=COMMIT, expected_version=(self.source / "VERSION").read_text().strip())
        self.assertEqual(checked["deployment"]["application_id"], "coup.jacobdanderson.net")
        self.assertEqual(checked["deployment"]["readiness"]["address_families"], ["ipv4", "ipv6"])
        self.assertEqual(checked["source_commit"], COMMIT)
        self.assertEqual(checked["research_source_sha256"],
                         json.loads((self.source / "security" / "approved-publication.json").read_text())[
                             "research_source_sha256"])
        with tarfile.open(self.archive_path, "r:gz") as archive:
            names = archive.getnames()
        self.assertTrue(names)
        self.assertTrue(all(name.startswith("dist/") for name in names))
        self.assertNotIn("security/approved-publication.json", names)
        self.assertNotIn("deployment-contract.json", names)

    def test_deterministic_archive_and_manifest(self) -> None:
        second = Path(self.temporary.name) / "second-release"
        build_release(self.source, second, source_commit=COMMIT,
                      source_clean=True, require_clean=False)
        for filename in (self.archive_path.name, "release-manifest.json", "SHA256SUMS"):
            self.assertEqual((self.release / filename).read_bytes(), (second / filename).read_bytes())

    def test_cli_imports_checker_from_any_working_directory(self) -> None:
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(ROOT / "scripts" / "release_artifact.py"), "--help"],
            cwd=self.temporary.name, check=False, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("source-bound, immutable Coup static release", result.stdout)

    def test_wrong_expected_identity_rejected(self) -> None:
        with self.assertRaisesRegex(ReleaseError, "expected commit"):
            verify_release(self.source, self.release, expected_commit="b" * 40)
        with self.assertRaisesRegex(ReleaseError, "expected version"):
            verify_release(self.source, self.release, expected_version="9.9.9")

    def test_archive_tamper_rejected(self) -> None:
        with self.archive_path.open("ab") as stream:
            stream.write(b"changed")
        with self.assertRaisesRegex(ReleaseError, "size differs"):
            verify_release(self.source, self.release, expected_commit=COMMIT)

    def test_symlink_rejected_even_after_outer_hashes_change(self) -> None:
        self.repack(kind="symlink")
        with self.assertRaisesRegex(ReleaseError, "Unsupported archive member"):
            verify_release(self.source, self.release, expected_commit=COMMIT)

    def test_path_traversal_rejected_even_after_outer_hashes_change(self) -> None:
        self.repack(replacement="dist/../escape")
        with self.assertRaisesRegex(ReleaseError, "Unsafe archive path"):
            verify_release(self.source, self.release, expected_commit=COMMIT)

    def test_duplicate_member_rejected_even_after_outer_hashes_change(self) -> None:
        self.repack(duplicate=True)
        with self.assertRaisesRegex(ReleaseError, "Archive inventory differs"):
            verify_release(self.source, self.release, expected_commit=COMMIT)

    def test_source_anchor_drift_rejected(self) -> None:
        anchor = self.source / "security" / "approved-publication.json"
        anchor.write_bytes(anchor.read_bytes() + b" ")
        with self.assertRaises(ReleaseError):
            verify_release(self.source, self.release, expected_commit=COMMIT)

    def test_source_contract_drift_rejected(self) -> None:
        contract = self.source / "deployment-contract.json"
        data = json.loads(contract.read_text())
        data["host_configuration"]["dns"] = "changed"
        contract.write_text(json.dumps(data) + "\n")
        with self.assertRaisesRegex(ReleaseError, "control hash differs"):
            verify_release(self.source, self.release, expected_commit=COMMIT)

    def test_source_site_policy_drift_rejected(self) -> None:
        policy = self.source / "security" / "site-policy.json"
        policy.write_bytes(policy.read_bytes() + b" ")
        with self.assertRaises(ReleaseError):
            verify_release(self.source, self.release, expected_commit=COMMIT)

    def test_release_requires_clean_source(self) -> None:
        with self.assertRaisesRegex(ReleaseError, "clean checkout"):
            build_release(self.source, Path(self.temporary.name) / "dirty",
                          source_commit=COMMIT, source_clean=False)

    def test_release_output_must_be_ignored_when_inside_checkout(self) -> None:
        # Model both fresh-checkout and locally configured ignore states in
        # an isolated repository instead of depending on the developer's Git.
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        output = self.source / ".ai-work" / "runs" / "release-assets"
        with self.assertRaisesRegex(ReleaseError, "not Git-ignored"):
            validate_output_directory(self.source, output)
        (self.source / ".git" / "info" / "exclude").write_text("/.ai-work/\n")
        validate_output_directory(self.source, output)
        with self.assertRaisesRegex(ReleaseError, "ignored .ai-work"):
            validate_output_directory(self.source, self.source / "dist" / "release-assets")
        with self.assertRaisesRegex(ReleaseError, "ignored .ai-work"):
            validate_output_directory(self.source, self.source / "release-assets")


if __name__ == "__main__":
    unittest.main()
