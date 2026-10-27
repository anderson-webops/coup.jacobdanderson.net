"""Build and independently check the static expansion evidence publication.

Only build-time validation imports trusted repository simulation code. The
public verifier uses the standard library and never extracts or executes
anything contained in the downloadable archive.
"""
from __future__ import annotations

from collections import Counter
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
from statistics import NormalDist
import tarfile

ROOT = Path(__file__).resolve().parent
STUDY_PATH = "research_results/2026-10-18-expansion"
PROFILES = ("inquisitor", "reformation", "combined")
POLICIES = ("honest", "bluff", "skeptic", "treasury", "shield", "converter", "information", "balanced")
FIELDS = ("honest", "bluffing", "skeptical", "adaptive", "mixed")
OPPONENTS = {"honest": "honest", "bluffing": "bluff", "skeptical": "skeptic", "adaptive": "balanced"}
STAGES = ("screening", "confirmation", "counter_search", "counters")
COUNTERS = (("inquisitor", 2), ("inquisitor", 6), ("reformation", 4), ("reformation", 10), ("combined", 4), ("combined", 10))
SOURCES = frozenset({"expansion_simulator.py", "expansion_policies.py", "expansion_study.py", "expansion_statistics.py",
    "test_expansion_study.py", "test_expansion_simulator.py", "audit_expansion_research.py", "test_expansion_audit.py"})
DOCS = ("docs/EXPANSION_RULES.md", "docs/EXPANSION_STUDY.md")
ROOT_FILES = {"plan.json", "preregistration.json", "selection.json", "counter_selection.json", "findings.json", "FINDINGS.md", "replay-audit.json"}
RAW_COLUMNS = ("profile", "stage", "players", "field", "candidate", "block", "rotation", "seed", "winner", "focal_seat", "won", "draw", "turns")
SUMMARY_COLUMNS = ("profile", "stage", "players", "field", "candidate", "blocks", "games", "wins", "draws", "win_rate", "mean_turns")
PUBLIC_FILES = ("expansion-evidence.tar.gz", "expansion-bundle-manifest.json", "expansion-findings.json", "expansion-confirmation.csv", "expansion-replay-audit.json")
MAX_BUNDLE_BYTES = 128 * 1024 * 1024
MAX_RAW_BYTES = 2 * 1024 * 1024 * 1024
MAX_GAMES = 10_000_000
MAX_FILES = 10000
SHA = re.compile(r"^[0-9a-f]{64}$")
SAFE = re.compile(r"^[a-z][a-z0-9_]*$")


class ExpansionPublicationError(ValueError):
    """Unreviewed, inconsistent or unsafe expansion publication bytes."""


def require(condition, message):
    if not condition:
        raise ExpansionPublicationError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate expansion JSON key")
        result[key] = value
    return result


def parse(raw):
    try:
        value = json.loads(raw, object_pairs_hook=_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ExpansionPublicationError("Nonfinite expansion JSON")))
    except (ValueError, UnicodeError) as exc:
        raise ExpansionPublicationError("Malformed expansion JSON") from exc
    require(raw == canonical(value), "Noncanonical expansion JSON")
    return value


def regular(path, *, base=None, maximum=MAX_BUNDLE_BYTES):
    path = Path(path)
    require(not path.is_symlink() and path.is_file(), f"Missing or linked expansion file: {path.name}")
    if base is not None:
        base = Path(base)
        require(not base.is_symlink() and base.is_dir(), "Linked or missing expansion source root")
        require(path.is_relative_to(base) and path.resolve().is_relative_to(base.resolve()),
                "Expansion input escapes its source root")
        current = path.parent
        while current != base:
            require(not current.is_symlink() and current.is_dir(), "Linked expansion input directory")
            current = current.parent
    require(path.stat().st_size <= maximum, "Expansion file exceeds size bound")
    raw = path.read_bytes()
    require(len(raw) <= maximum, "Expansion file exceeds read bound")
    return raw


def integer(value, label, minimum=0, maximum=None):
    require(not isinstance(value, bool), f"Invalid expansion integer: {label}")
    if isinstance(value, int):
        result = value
    else:
        require(isinstance(value, str) and value.isascii() and value.isdecimal(), f"Invalid expansion integer: {label}")
        result = int(value)
        require(str(result) == value, f"Noncanonical expansion integer: {label}")
    require(result >= minimum and (maximum is None or result <= maximum), f"Expansion integer outside range: {label}")
    return result


def safe_name(name):
    require(isinstance(name, str) and bool(name) and "\\" not in name and not name.startswith("/"), "Unsafe expansion archive name")
    path = PurePosixPath(name)
    require(path.as_posix() == name and ".." not in path.parts and "." not in path.parts and not name.endswith("/"), "Unsafe expansion archive path")
    return name


def _validate_study(study_dir, source_root):
    # These are trusted source modules beside the builder, never bundled code.
    from expansion_study import verify_study
    require(Path(source_root).resolve() == ROOT, "Build-time scientific validation requires this trusted source checkout")
    findings = verify_study(study_dir)
    replay = parse(regular(Path(study_dir) / "replay-audit.json"))
    # The full replay is a separate scientific gate. Static verification below
    # binds its receipt to every current stage/source hash and independently
    # reconciles all raw results without unnecessarily repeating those replays.
    require(replay.get("status") == "passed", "Missing successful expansion independent replay receipt")
    return findings, replay


def _collect_files(repo_root, study_dir):
    plan = parse(regular(study_dir / "plan.json", base=repo_root))
    require(set(plan.get("source_sha256", {})) == SOURCES, "Expansion source inventory differs")
    relative = set(ROOT_FILES) | {"sources/" + name for name in SOURCES}
    for stage in STAGES:
        manifest = parse(regular(study_dir / stage / "manifest.json", base=repo_root))
        require(isinstance(manifest.get("files"), dict), "Missing expansion stage inventory")
        relative.add(stage + "/manifest.json")
        relative.update(stage + "/" + safe_name(name) for name in manifest["files"])
    observed = set()
    for path in study_dir.rglob("*"):
        require(not path.is_symlink(), "Expansion study contains a symlink")
        if path.is_file():
            observed.add(path.relative_to(study_dir).as_posix())
        else:
            require(path.is_dir(), "Expansion study contains a nonregular entry")
    require(observed == relative, "Expansion study file inventory differs")
    allowed_dirs = {str(PurePosixPath(name).parent) for name in relative} - {"."}
    require({p.relative_to(study_dir).as_posix() for p in study_dir.rglob("*") if p.is_dir()} == allowed_dirs,
            "Expansion study directory inventory differs")
    files = {STUDY_PATH + "/" + name: study_dir / name for name in relative}
    files.update({name: repo_root / name for name in SOURCES | set(DOCS)})
    return files


def _atomic(path, raw):
    path = Path(path)
    require(not path.is_symlink(), "Refusing linked expansion output")
    temporary = path.with_name(path.name + ".part")
    require(not temporary.exists() and not temporary.is_symlink(), "Interrupted expansion output needs inspection")
    with temporary.open("xb") as file:
        file.write(raw)
    temporary.replace(path)


def build_expansion_publication(repo_root, evidence_dir, study_dir=None):
    """Return embedded data, explicit approval data and publication metadata.

    This does not update the approval file. The caller reviews the returned
    anchor alongside all changed public bytes before approving publication.
    """
    require(__debug__, "Optimized Python cannot build expansion evidence")
    repo_root = Path(repo_root).resolve()
    study_dir = Path(study_dir) if study_dir is not None else repo_root / STUDY_PATH
    require(not study_dir.is_symlink() and study_dir.is_relative_to(repo_root) and
            study_dir.resolve().is_relative_to(repo_root), "Linked or escaping expansion study root")
    evidence_dir = Path(evidence_dir)
    require(not evidence_dir.is_symlink() and evidence_dir.is_relative_to(repo_root) and
            evidence_dir.resolve().is_relative_to(repo_root), "Unsafe expansion output root")
    ancestor = evidence_dir
    while ancestor != repo_root:
        require(not ancestor.is_symlink(), "Linked expansion output directory")
        ancestor = ancestor.parent
    findings, replay = _validate_study(study_dir, repo_root)
    files = _collect_files(repo_root, study_dir)
    contents = {safe_name(name): regular(path, base=repo_root) for name, path in sorted(files.items())}
    require(0 < len(contents) <= MAX_FILES and sum(map(len, contents.values())) <= MAX_BUNDLE_BYTES, "Expansion bundle exceeds reviewed bounds")
    manifest = {name: {"sha256": sha(raw), "size": len(raw)} for name, raw in contents.items()}
    output = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=output, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for name, raw in contents.items():
                info = tarfile.TarInfo(name)
                info.size = len(raw); info.mode = 0o644; info.mtime = 0
                info.uid = info.gid = 0; info.uname = info.gname = ""
                archive.addfile(info, io.BytesIO(raw))
    bundle = output.getvalue()
    for name, path in files.items():
        require(regular(path, base=repo_root) == contents[name], "Expansion source changed while bundling")
    plan = parse(contents[STUDY_PATH + "/plan.json"])
    manifest_bytes = canonical(manifest)
    anchor = {"schema_version": 1, "study_path": STUDY_PATH,
        "plan_sha256": sha(contents[STUDY_PATH + "/plan.json"]),
        "findings_sha256": sha(contents[STUDY_PATH + "/findings.json"]),
        "replay_audit_sha256": sha(contents[STUDY_PATH + "/replay-audit.json"]),
        "source_sha256": plan["source_sha256"], "bundle_manifest_sha256": sha(manifest_bytes), "bundle_sha256": sha(bundle)}
    publication = {"expansion_snapshot": "2026-10-18", "expansion_study_games": findings["total_games"],
        "expansion_confirmation_games": next(s["games"] for s in findings["stages"] if s["stage"] == "confirmation"),
        "expansion_replayed_games": replay["total_replayed_games"]}
    evidence_dir.mkdir(parents=True, exist_ok=True)
    outputs = {"expansion-evidence.tar.gz": bundle, "expansion-bundle-manifest.json": manifest_bytes,
        "expansion-findings.json": contents[STUDY_PATH + "/findings.json"],
        "expansion-confirmation.csv": contents[STUDY_PATH + "/confirmation/summaries.csv"],
        "expansion-replay-audit.json": contents[STUDY_PATH + "/replay-audit.json"]}
    for name, raw in outputs.items():
        _atomic(evidence_dir / name, raw)
    embedded = {"expansion": findings, "expansion_configs": plan["configurations"]}
    verify_expansion_bundle(repo_root, evidence_dir, embedded, {"expansion_study": anchor}, publication)
    return {**embedded, "anchor": anchor, "publication": publication}


def _archive(evidence, anchor):
    inventory_bytes = regular(evidence / "expansion-bundle-manifest.json", base=evidence)
    bundle = regular(evidence / "expansion-evidence.tar.gz", base=evidence)
    require(sha(inventory_bytes) == anchor["bundle_manifest_sha256"] and sha(bundle) == anchor["bundle_sha256"],
            "Expansion archive differs from reviewed external anchor")
    inventory = parse(inventory_bytes)
    require(isinstance(inventory, dict) and 0 < len(inventory) <= MAX_FILES, "Invalid expansion archive inventory")
    for name, metadata in inventory.items():
        safe_name(name)
        require(isinstance(metadata, dict) and set(metadata) == {"size", "sha256"} and
                isinstance(metadata["sha256"], str) and SHA.fullmatch(metadata["sha256"]), "Invalid expansion inventory metadata")
        integer(metadata["size"], "archive member size", maximum=MAX_BUNDLE_BYTES)
    require(sum(r["size"] for r in inventory.values()) <= MAX_BUNDLE_BYTES, "Expansion archive exceeds total bound")
    saved = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(bundle), mode="r:gz") as archive:
            for member in archive:
                name = safe_name(member.name)
                require(member.isfile() and name in inventory and name not in saved, "Unsafe, repeated or unplanned expansion archive member")
                require(member.size == inventory[name]["size"], "Expansion member size differs")
                require(member.mode == 0o644 and member.mtime == 0 and member.uid == 0 and member.gid == 0 and
                        member.uname == "" and member.gname == "" and not member.pax_headers,
                        "Expansion archive metadata is not deterministic")
                file = archive.extractfile(member)
                require(file is not None, "Unreadable expansion member")
                raw = file.read(member.size + 1)
                require(len(raw) == member.size and sha(raw) == inventory[name]["sha256"], "Expansion member digest differs")
                saved[name] = raw
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise ExpansionPublicationError("Malformed expansion archive") from exc
    require(saved.keys() == inventory.keys(), "Expansion archive member inventory differs")
    return saved


def _job(profile, players, field, candidate, blocks):
    return {"profile": profile, "players": players, "field": field, "candidate": candidate, "blocks": blocks}


def _filename(job):
    return f"{job['profile']}-{job['players']}-{job['field']}-{job['candidate']}.csv.gz"


def _seed(profile, stage, players, field, block):
    return int(hashlib.sha256(f"coup-expansion-study-v1:{profile}:{stage}:{players}:{field}:{block}".encode("ascii")).hexdigest(), 16)


def _raw_summary(raw, stage, job, expanded_bytes):
    n, blocks = job["players"], job["blocks"]
    seen, block_wins = set(), [0] * blocks
    wins = draws = turns = 0
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as compressed:
            def line():
                value = compressed.readline(2049)
                require(len(value) <= 2048, "Expansion raw row exceeds bound")
                expanded_bytes[0] += len(value)
                require(expanded_bytes[0] <= MAX_RAW_BYTES, "Expansion raw decompression exceeds bound")
                return value
            header = next(csv.reader([line().decode("ascii")]))
            require(tuple(header) == RAW_COLUMNS, "Expansion raw schema differs")
            while True:
                text = line()
                if not text:
                    break
                values = next(csv.reader([text.decode("ascii")]))
                require(len(values) == len(RAW_COLUMNS), "Malformed expansion outcome row")
                row = dict(zip(RAW_COLUMNS, values))
                require(tuple(row[k] for k in RAW_COLUMNS[:5]) == (job["profile"], stage, str(n), job["field"], job["candidate"]), "Expansion outcome belongs to another planned job")
                block = integer(row["block"], "block", maximum=blocks-1)
                rotation = integer(row["rotation"], "rotation", maximum=n-1)
                focal = integer(row["focal_seat"], "focal seat", maximum=n-1)
                winner = None if row["winner"] == "" else integer(row["winner"], "winner", maximum=n-1)
                won = integer(row["won"], "won", maximum=1)
                draw = integer(row["draw"], "draw", maximum=1)
                turn = integer(row["turns"], "turns", minimum=1, maximum=1000)
                require((block, rotation) not in seen and focal == rotation and won == int(winner == focal) and draw == int(winner is None), "Expansion rotation, focal identity or outcome flags differ")
                require(integer(row["seed"], "seed") == _seed(job["profile"], stage, n, job["field"], block) and (not draw or turn == 1000), "Expansion seed or capped outcome differs")
                seen.add((block, rotation)); block_wins[block] += won
                wins += won; draws += draw; turns += turn
    except (OSError, EOFError, UnicodeError, csv.Error, StopIteration) as exc:
        raise ExpansionPublicationError("Unreadable expansion raw outcomes") from exc
    games = n * blocks
    require(len(seen) == games, "Incomplete expansion rotation panel")
    return {"profile": job["profile"], "stage": stage, "players": n, "field": job["field"],
        "candidate": job["candidate"], "blocks": blocks, "games": games, "wins": wins, "draws": draws,
        "win_rate": wins/games, "mean_turns": turns/games}, block_wins


def _stage(saved, plan, stage, jobs, expanded_bytes):
    prefix = STUDY_PATH + "/" + stage + "/"
    stage_plan = parse(saved[prefix + "plan.json"])
    require(stage_plan == {"stage": stage, "global_plan_sha256": sha(saved[STUDY_PATH + "/plan.json"]),
        "source_sha256": plan["source_sha256"], "jobs": jobs}, "Expansion stage plan differs from independent schedule")
    names = [_filename(job) for job in jobs]
    require(len(names) == len(set(names)), "Duplicate expansion job")
    files = {"plan.json", "summaries.csv", *names, *(str(PurePosixPath(name).with_suffix(".diagnostics.json")) for name in names)}
    manifest = parse(saved[prefix + "manifest.json"])
    require(manifest == {"stage": stage, "plan_sha256": sha(saved[prefix + "plan.json"]),
        "global_plan_sha256": sha(saved[STUDY_PATH + "/plan.json"]), "source_sha256": plan["source_sha256"],
        "scheduled_games": sum(j["players"]*j["blocks"] for j in jobs), "files": {name: sha(saved[prefix+name]) for name in sorted(files)}}, "Expansion stage manifest differs")
    summaries, blocks, diagnostics = [], {}, Counter()
    for job, name in zip(jobs, names):
        summary, wins = _raw_summary(saved[prefix+name], stage, job, expanded_bytes)
        diagnostic = parse(saved[prefix + str(PurePosixPath(name).with_suffix(".diagnostics.json"))])
        require(set(diagnostic) == {"stage", "job", "summary", "raw_sha256", "diagnostics"} and diagnostic["stage"] == stage and
            diagnostic["job"] == job and diagnostic["summary"] == summary and diagnostic["raw_sha256"] == sha(saved[prefix+name]) and
            isinstance(diagnostic["diagnostics"], dict), "Expansion diagnostic differs from raw outcomes")
        for label, count in diagnostic["diagnostics"].items():
            require(isinstance(label, str) and bool(label), "Invalid expansion mechanism label")
            diagnostics[label] += integer(count, "mechanism count")
        summaries.append(summary)
        if stage in ("confirmation", "counters"):
            blocks[job["profile"], job["players"], job["field"], job["candidate"]] = wins
    try:
        reader = csv.DictReader(io.StringIO(saved[prefix+"summaries.csv"].decode("utf-8")))
        require(tuple(reader.fieldnames or ()) == SUMMARY_COLUMNS and list(reader) == [
            {key: str(row[key]) for key in SUMMARY_COLUMNS} for row in summaries], "Expansion summary differs from independently counted raw outcomes")
    except (UnicodeError, csv.Error) as exc:
        raise ExpansionPublicationError("Unreadable expansion summary") from exc
    return {"stage": stage, "jobs": len(jobs), "games": sum(r["games"] for r in summaries), "draws": sum(r["draws"] for r in summaries),
        "manifest_sha256": sha(saved[prefix+"manifest.json"]), "summaries": summaries, "block_wins": blocks,
        "diagnostics": dict(sorted(diagnostics.items())), "members": {prefix+name for name in files | {"manifest.json"}}, "job_list": jobs}


def _selection(rows):
    result = []
    for profile in PROFILES:
        for n in range(2, 11):
            cells = [r for r in rows if (r["profile"], r["players"]) == (profile, n)]
            require(len(cells) == 40 and {(r["field"], r["candidate"]) for r in cells} == {(f,p) for f in FIELDS for p in POLICIES}, "Expansion screening cell incomplete")
            scores = {p: sum(r["wins"] for r in cells if r["candidate"] == p) for p in POLICIES}
            ranking = sorted(POLICIES, key=lambda p: (-scores[p], p))
            result.append({"profile": profile, "players": n, "first": ranking[0], "second": ranking[1], "screening_rank": ranking})
    return {"finalists": result}


def _counter_selection(rows, selection):
    ranks = {(r["profile"], r["players"]): r["first"] for r in selection["finalists"]}
    result = []
    for profile, n in COUNTERS:
        target, field = ranks[profile,n], "vs_" + ranks[profile,n]
        cells = [r for r in rows if (r["profile"], r["players"], r["field"]) == (profile,n,field)]
        require(len(cells) == 8 and {r["candidate"] for r in cells} == set(POLICIES), "Expansion counter cell incomplete")
        best = min((r for r in cells if r["candidate"] != target), key=lambda r: (-r["wins"],r["candidate"]))
        result.append({"profile": profile, "players": n, "field": field, "first": best["candidate"], "second": target})
    return {"pairs": result}


def _pair(row, field, stage_result, family_size, summaries):
    profile,n,first,second = row["profile"],row["players"],row["first"],row["second"]
    a = stage_result["block_wins"][profile,n,field,first]
    b = stage_result["block_wins"][profile,n,field,second]
    count = len(a)
    require(count == len(b) and count >= 2, "Expansion paired blocks differ")
    differences = [x-y for x,y in zip(a,b)]
    total = sum(differences)
    difference = total/(n*count)
    variance = (count*sum(v*v for v in differences)-total*total)/(count*(count-1)*n*n)
    normal_half = NormalDist().inv_cdf(1-.05/(2*family_size))*math.sqrt(variance/count)
    strict_half = math.sqrt(2*math.log(2*family_size/.05)/count)
    lo,hi = max(-1.,difference-normal_half),min(1.,difference+normal_half)
    slo,shi = max(-1.,difference-strict_half),min(1.,difference+strict_half)
    lookup = {r["candidate"]:r for r in summaries if (r["profile"],r["players"],r["field"]) == (profile,n,field)}
    return {"profile":profile,"field":field,"first":first,"second":second,"players":n,"blocks":count,
        "games_per_candidate":n*count,"first_wins":sum(a),"second_wins":sum(b),
        "first_draws":lookup[first]["draws"],"second_draws":lookup[second]["draws"],
        "first_rate":sum(a)/(n*count),"second_rate":sum(b)/(n*count),"difference":difference,
        "normal_family_lower":lo,"normal_family_upper":hi,"conservative_family_lower":slo,"conservative_family_upper":shi,
        "normal_supports_positive":lo>0,"normal_supports_practical":lo>.02,
        "conservative_supports_positive":slo>0,"conservative_supports_practical":slo>.02,
        "family_size":family_size,"alpha":.05,"practical_threshold":.02}


def _same(saved, expected, path=()):
    require(type(saved) is type(expected), "Expansion findings type differs")
    if isinstance(expected,dict):
        require(saved.keys()==expected.keys(),"Expansion findings key inventory differs")
        for key in expected:_same(saved[key],expected[key],path+(key,))
    elif isinstance(expected,list):
        require(len(saved)==len(expected),"Expansion findings length differs")
        for i,value in enumerate(expected):_same(saved[i],value,path+(i,))
    elif isinstance(expected,float):
        require(math.isfinite(saved) and math.isfinite(expected),"Nonfinite expansion findings")
        if saved != expected:
            require(len(path)==3 and path[0] in ("confirmation_pairs","counters") and
                path[-1] in {"normal_family_lower","normal_family_upper","conservative_family_lower","conservative_family_upper"} and
                saved != 0 and expected != 0 and (saved>0)==(expected>0) and abs(saved-expected)<=1e-14,
                "Expansion numerical finding differs from raw calculation")
    else:require(saved==expected,"Expansion finding differs from raw evidence")


def _verify_plan(plan, saved, anchor):
    fixed = {"schema_version":1,"profiles":list(PROFILES),"players":list(range(2,11)),"policies":list(POLICIES),
        "fields":list(FIELDS),"opponents":OPPONENTS,"mixed_pool":list(POLICIES),"stages":list(STAGES),
        "deck_copies":{str(n):3 if n<=6 else 4 if n<=8 else 5 for n in range(2,11)},"max_turns":1000,"strict_every_action":True,
        "raw_columns":list(RAW_COLUMNS),"confirmation_family_size":135,"counter_family_size":6,"counter_settings":[list(r) for r in COUNTERS],
        "seed_rule":"SHA256 ASCII coup-expansion-study-v1:profile:stage:players:field:block, big-endian integer",
        "lineup_rule":"identity 0 focal; mixed pool[(block+j)%8] for j=0..n-2, reverse on odd pool cycles; rotate every identity right by rotation",
        "selection_rule":"per profile/player count, rank mean screening win rate equally across five fields; top two; ties lexical policy ID",
        "counter_target_rule":"screening rank first per specified profile/player count",
        "counter_selection_rule":"highest search win rate excluding target; ties lexical policy ID",
        "decision_rng_rule":"engine domain-separated per participant identity, independent from environment/deck randomness",
        "inference":{"alpha":.05,"practical_threshold":.02,"independent_unit":"complete rotation block",
            "intervals":["approximate Bonferroni normal","conservative simultaneous Hoeffding"],
            "draw_denominator":"all scheduled games","no_confirmation_retuning":True}}
    for key,value in fixed.items():
        require(type(plan.get(key)) is type(value) and plan[key]==value,f"Unsupported expansion protocol: {key}")
    require(set(plan.get("blocks",{}))==set(STAGES),"Expansion block inventory differs")
    for stage in STAGES:integer(plan["blocks"][stage],"planned blocks",minimum=2,maximum=100000)
    planned = 3*sum(range(2,11))*5*(8*plan["blocks"]["screening"]+2*plan["blocks"]["confirmation"]) + sum(n for _,n in COUNTERS)*(8*plan["blocks"]["counter_search"]+2*plan["blocks"]["counters"])
    require(planned <= MAX_GAMES,"Expansion planned game budget exceeds public verifier bound")
    require(isinstance(plan.get("configurations"),dict) and set(plan["configurations"])==set(POLICIES),"Expansion configuration catalogue differs")
    require(plan.get("source_sha256")==anchor["source_sha256"] and set(plan["source_sha256"])==SOURCES,"Expansion source hashes differ from external approval")
    for name,expected in plan["source_sha256"].items():
        require(isinstance(expected,str) and SHA.fullmatch(expected) and sha(saved[name])==expected and
            sha(saved[STUDY_PATH+"/sources/"+name])==expected,"Expansion source snapshot changed")
    registration=plan.get("preregistration",{})
    require(set(registration)=={"kind","independent_timestamp_registry","created_utc"} and
        registration.get("kind")=="local hashed source and protocol snapshot" and registration.get("independent_timestamp_registry") is False and
        isinstance(registration.get("created_utc"),str),"Expansion local registration disclosure differs")
    require(parse(saved[STUDY_PATH+"/preregistration.json"])=={"plan_sha256":anchor["plan_sha256"],"source_sha256":plan["source_sha256"],
        "created_utc":registration["created_utc"],"kind":registration["kind"],"independent_timestamp_registry":False},"Expansion registration receipt differs")


def verify_expansion_bundle(root,evidence,embedded,anchor,publication):
    """Verify an extracted static site against independently reviewed approval."""
    require(__debug__,"Optimized Python cannot verify expansion publication")
    root,evidence=Path(root),Path(evidence)
    require(not evidence.is_symlink() and evidence.is_dir(),"Linked or missing expansion evidence root")
    approval=anchor.get("expansion_study")
    require(isinstance(approval,dict) and set(approval)=={"schema_version","study_path","plan_sha256","findings_sha256","replay_audit_sha256","source_sha256","bundle_manifest_sha256","bundle_sha256"} and
        approval["schema_version"]==1 and approval["study_path"]==STUDY_PATH,"Missing reviewed expansion approval")
    for key in ("plan_sha256","findings_sha256","replay_audit_sha256","bundle_manifest_sha256","bundle_sha256"):
        require(isinstance(approval[key],str) and SHA.fullmatch(approval[key]),"Invalid expansion approval digest")
    try:
        saved=_archive(evidence,approval)
        prefix=STUDY_PATH+"/"
        require(sha(saved[prefix+"plan.json"])==approval["plan_sha256"] and sha(saved[prefix+"findings.json"])==approval["findings_sha256"] and
            sha(saved[prefix+"replay-audit.json"])==approval["replay_audit_sha256"],"Expansion approved evidence digests differ")
        plan=parse(saved[prefix+"plan.json"])
        _verify_plan(plan,saved,approval)
        findings=parse(saved[prefix+"findings.json"])
        require(embedded.get("expansion")==findings and embedded.get("expansion_configs")==plan["configurations"],"Expansion embedded data or configurations differ")
        for filename,bundled in (("expansion-findings.json","findings.json"),("expansion-confirmation.csv","confirmation/summaries.csv"),("expansion-replay-audit.json","replay-audit.json")):
            require(regular(evidence/filename,base=evidence)==saved[prefix+bundled],"Expansion download differs from bundle")
        expanded_bytes=[0]
        screen_jobs=[_job(p,n,f,c,plan["blocks"]["screening"]) for p in PROFILES for n in range(2,11) for f in FIELDS for c in POLICIES]
        screen=_stage(saved,plan,"screening",screen_jobs,expanded_bytes)
        selection=_selection(screen["summaries"])
        require(parse(saved[prefix+"selection.json"])==selection,"Expansion selected finalists differ from screening")
        confirmation_jobs=[_job(r["profile"],r["players"],f,r[k],plan["blocks"]["confirmation"]) for r in selection["finalists"] for f in FIELDS for k in ("first","second")]
        confirmation=_stage(saved,plan,"confirmation",confirmation_jobs,expanded_bytes)
        ranks={(r["profile"],r["players"]):r["first"] for r in selection["finalists"]}
        search_jobs=[_job(p,n,"vs_"+ranks[p,n],c,plan["blocks"]["counter_search"]) for p,n in COUNTERS for c in POLICIES]
        search=_stage(saved,plan,"counter_search",search_jobs,expanded_bytes)
        counter_selection=_counter_selection(search["summaries"],selection)
        require(parse(saved[prefix+"counter_selection.json"])==counter_selection,"Expansion selected counters differ from search")
        counter_jobs=[_job(r["profile"],r["players"],r["field"],r[k],plan["blocks"]["counters"]) for r in counter_selection["pairs"] for k in ("first","second")]
        counters=_stage(saved,plan,"counters",counter_jobs,expanded_bytes)
        stages=(screen,confirmation,search,counters)
        require(sum(s["games"] for s in stages)<=MAX_GAMES,"Expansion scheduled game budget exceeds bound")
        expected_members={prefix+n for n in ROOT_FILES}|{prefix+"sources/"+n for n in SOURCES}|SOURCES|set(DOCS)
        for stage in stages:expected_members.update(stage["members"])
        require(set(saved)==expected_members,"Expansion archive logical inventory differs")
        recommendations=[]
        for row in selection["finalists"]:
            for candidate in (row["first"],row["second"]):
                cells=[r for r in confirmation["summaries"] if (r["profile"],r["players"],r["candidate"])==(row["profile"],row["players"],candidate)]
                wins,games=sum(r["wins"] for r in cells),sum(r["games"] for r in cells)
                worst=min(cells,key=lambda r:(r["wins"],r["field"]))
                recommendations.append({"profile":row["profile"],"players":row["players"],"candidate":candidate,
                    "wins":wins,"games":games,"equal_field_mean":wins/games,"worst_field":worst["field"],"worst_rate":worst["win_rate"],
                    "draws":sum(r["draws"] for r in cells),"screening_position":1 if candidate==row["first"] else 2})
        computed={"schema_version":1,"plan_sha256":approval["plan_sha256"],"source_sha256":plan["source_sha256"],"preregistration":plan["preregistration"],
            "total_games":sum(s["games"] for s in stages),"total_draws":sum(s["draws"] for s in stages),
            "stages":[{k:s[k] for k in ("stage","games","draws","jobs","manifest_sha256")} for s in stages],
            "screening":screen["summaries"],"confirmation":confirmation["summaries"],
            "confirmation_pairs":[_pair(r,f,confirmation,135,confirmation["summaries"]) for r in selection["finalists"] for f in FIELDS],
            "counters":[_pair(r,r["field"],counters,6,counters["summaries"]) for r in counter_selection["pairs"]],
            "recommendations":recommendations,"diagnostics":{s["stage"]:s["diagnostics"] for s in stages},
            "limitations":["finite computer-policy population","no human negotiation or cross-game learning",
                "two screening-selected policies confirmed per profile/player count","approximate intervals and conservative bounds reported separately"]}
        _same(findings,computed)
        replay=parse(saved[prefix+"replay-audit.json"])
        require(replay.get("schema_version")==1 and replay.get("status")=="passed" and replay.get("global_plan_sha256")==approval["plan_sha256"] and
            replay.get("source_sha256")==plan["source_sha256"] and replay.get("audit_source_sha256")==sha(saved["audit_expansion_research.py"]) and
            [r.get("stage") for r in replay.get("stages",[])]==list(STAGES),"Expansion independent audit receipt identity differs")
        for entry,stage in zip(replay["stages"],stages):
            replayed=sum(j["players"]*len({0,j["blocks"]//2,j["blocks"]-1}) for j in stage["job_list"])
            require(entry=={"stage":stage["stage"],"jobs":stage["jobs"],"raw_games":stage["games"],"draws":stage["draws"],"replayed_games":replayed,
                "stage_plan_sha256":sha(saved[prefix+stage["stage"]+"/plan.json"]),"stage_manifest_sha256":stage["manifest_sha256"],
                "replay_identity_outcomes_sha256":entry.get("replay_identity_outcomes_sha256")} and
                isinstance(entry.get("replay_identity_outcomes_sha256"),str) and SHA.fullmatch(entry["replay_identity_outcomes_sha256"]),"Expansion independent stage receipt differs")
        require(replay.get("total_jobs")==sum(s["jobs"] for s in stages) and replay.get("total_raw_games")==computed["total_games"] and
            replay.get("total_draws")==computed["total_draws"] and replay.get("total_replayed_games")==sum(s["replayed_games"] for s in replay["stages"]),"Expansion independent audit totals differ")
        expected_publication={"expansion_snapshot":"2026-10-18","expansion_study_games":computed["total_games"],
            "expansion_confirmation_games":confirmation["games"],"expansion_replayed_games":replay["total_replayed_games"]}
        require(all(publication.get(k)==v for k,v in expected_publication.items()),"Expansion publication totals differ")
        if (root/STUDY_PATH/"plan.json").exists():
            for name,raw in saved.items():
                require(regular(root/name,base=root)==raw,"Expansion public/source bytes differ")
        return {"status":"passed","total_games":computed["total_games"],"raw_bytes_checked":expanded_bytes[0],
            "total_replayed_games":replay["total_replayed_games"],"files":len(saved)}
    except (KeyError,TypeError,AttributeError) as exc:
        raise ExpansionPublicationError("Incomplete expansion evidence structure") from exc
