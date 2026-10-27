"""Locally preregister, run and audit separate Coup expansion experiments.

The frozen base-game studies are never imported or modified. A local hashed
snapshot is preregistration evidence, not an independently timestamped registry.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import re
import time

from expansion_statistics import ExpansionDataError, integer, paired_compare, panel

ROOT = Path(__file__).resolve().parent
DEFAULT_STUDY = ROOT / "research_results" / "2026-10-18-expansion"
SOURCE_FILES = ("expansion_simulator.py", "expansion_policies.py", "expansion_study.py",
                "expansion_statistics.py", "test_expansion_study.py", "test_expansion_simulator.py",
                "audit_expansion_research.py", "test_expansion_audit.py")
PROFILES = ("inquisitor", "reformation", "combined")
POLICIES = ("honest", "bluff", "skeptic", "treasury", "shield", "converter", "information", "balanced")
FIELDS = ("honest", "bluffing", "skeptical", "adaptive", "mixed")
OPPONENTS = {"honest": "honest", "bluffing": "bluff", "skeptical": "skeptic", "adaptive": "balanced"}
STAGES = ("screening", "confirmation", "counter_search", "counters")
COUNTER_SETTINGS = (("inquisitor", 2), ("inquisitor", 6), ("reformation", 4),
                    ("reformation", 10), ("combined", 4), ("combined", 10))
RAW_COLUMNS = ("profile", "stage", "players", "field", "candidate", "block", "rotation",
               "seed", "winner", "focal_seat", "won", "draw", "turns")
SUMMARY_COLUMNS = ("profile", "stage", "players", "field", "candidate", "blocks", "games",
                   "wins", "draws", "win_rate", "mean_turns")
SAFE_NAME = re.compile(r"^[a-z0-9_]+$")


class ExpansionStudyError(ValueError):
    """An expansion protocol, source snapshot or recorded panel changed."""


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _unique_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ExpansionStudyError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ExpansionStudyError(f"regular JSON file required: {path}")
    try:
        value = json.loads(path.read_text(), object_pairs_hook=_unique_keys,
                           parse_constant=lambda _: (_ for _ in ()).throw(ExpansionStudyError("nonfinite JSON")))
    except (OSError, ValueError) as exc:
        raise ExpansionStudyError(f"invalid JSON: {path}") from exc
    if path.read_bytes() != json_bytes(value):
        raise ExpansionStudyError(f"noncanonical JSON: {path}")
    return value


def freeze_json(path, value):
    path = Path(path)
    value = json.loads(json_bytes(value))
    if path.exists() or path.is_symlink():
        if read_json(path) != value:
            raise ExpansionStudyError(f"frozen file differs: {path}; use a new study directory")
    else:
        with path.open("xb") as file:
            file.write(json_bytes(value))
    return value


def source_hashes():
    result = {}
    for name in SOURCE_FILES:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ExpansionStudyError(f"execution source missing or symlinked: {name}")
        result[name] = digest(path)
    return result


def _configuration_catalogue():
    from expansion_policies import CONFIGS
    if set(CONFIGS) != set(POLICIES):
        raise ExpansionStudyError("policy catalogue differs from the eight preregistered IDs")
    return json.loads(json_bytes({name: asdict(value) if is_dataclass(value) else value
                                  for name, value in sorted(CONFIGS.items())}))


def _bounds(value, name, minimum=2):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= 100000:
        raise ExpansionStudyError(f"{name} must be an integer in [{minimum},100000]")
    return value


def freeze_plan(directory, *, screen_blocks=32, confirmation_blocks=1000,
                counter_search_blocks=32, counter_blocks=1000):
    """Freeze exact code and settings before outcomes; never rewrite a plan."""
    directory = Path(directory)
    if directory.is_symlink():
        raise ExpansionStudyError("study directory may not be a symlink")
    directory = directory.resolve()
    if directory == ROOT or not any(directory.is_relative_to(ROOT / folder)
                                    for folder in ("research_results", ".ai-work")):
        raise ExpansionStudyError("new studies must live in this repository's research_results or .ai-work")
    if directory.is_relative_to(ROOT / "research_results" / "2026-10-12-v2"):
        raise ExpansionStudyError("cannot write over the frozen base study")
    counts = {"screening": _bounds(screen_blocks, "screen_blocks"),
              "confirmation": _bounds(confirmation_blocks, "confirmation_blocks"),
              "counter_search": _bounds(counter_search_blocks, "counter_search_blocks"),
              "counters": _bounds(counter_blocks, "counter_blocks")}
    directory.mkdir(parents=True, exist_ok=True)
    existing = read_json(directory / "plan.json") if (directory / "plan.json").exists() else None
    plan = {
        "schema_version": 1, "study": "Coup expansion strategy study",
        "preregistration": {"kind": "local hashed source and protocol snapshot",
                            "independent_timestamp_registry": False,
                            "created_utc": existing["preregistration"]["created_utc"] if existing else
                            datetime.now(timezone.utc).isoformat()},
        "python": platform.python_version(), "source_sha256": source_hashes(),
        "profiles": list(PROFILES), "players": list(range(2, 11)),
        "deck_copies": {str(n): 3 if n <= 6 else 4 if n <= 8 else 5 for n in range(2, 11)},
        "policies": list(POLICIES), "configurations": _configuration_catalogue(),
        "fields": list(FIELDS), "opponents": OPPONENTS, "mixed_pool": list(POLICIES),
        "blocks": counts, "max_turns": 1000, "strict_every_action": True,
        "raw_columns": list(RAW_COLUMNS), "stages": list(STAGES),
        "seed_rule": "SHA256 ASCII coup-expansion-study-v1:profile:stage:players:field:block, big-endian integer",
        "lineup_rule": "identity 0 focal; mixed pool[(block+j)%8] for j=0..n-2, reverse on odd pool cycles; rotate every identity right by rotation",
        "decision_rng_rule": "engine domain-separated per participant identity, independent from environment/deck randomness",
        "selection_rule": "per profile/player count, rank mean screening win rate equally across five fields; top two; ties lexical policy ID",
        "confirmation_family_size": len(PROFILES) * 9 * len(FIELDS),
        "counter_settings": [list(setting) for setting in COUNTER_SETTINGS],
        "counter_target_rule": "screening rank first per specified profile/player count",
        "counter_selection_rule": "highest search win rate excluding target; ties lexical policy ID",
        "counter_family_size": len(COUNTER_SETTINGS),
        "inference": {"alpha": 0.05, "practical_threshold": 0.02,
                      "independent_unit": "complete rotation block",
                      "intervals": ["approximate Bonferroni normal", "conservative simultaneous Hoeffding"],
                      "draw_denominator": "all scheduled games", "no_confirmation_retuning": True},
    }
    freeze_json(directory / "plan.json", plan)
    freeze_json(directory / "preregistration.json", {"plan_sha256": digest(directory / "plan.json"),
        "source_sha256": plan["source_sha256"], "created_utc": plan["preregistration"]["created_utc"],
        "kind": plan["preregistration"]["kind"], "independent_timestamp_registry": False})
    snapshots = directory / "sources"
    if snapshots.is_symlink():
        raise ExpansionStudyError("source snapshots may not be symlinked")
    snapshots.mkdir(exist_ok=True)
    for name in SOURCE_FILES:
        path = snapshots / name
        content = (ROOT / name).read_bytes()
        if path.exists() or path.is_symlink():
            if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
                raise ExpansionStudyError(f"source snapshot differs: {name}")
        else:
            with path.open("xb") as file:
                file.write(content)
    _check_plan(directory)
    return plan


def _check_plan(directory):
    directory = Path(directory)
    plan = read_json(directory / "plan.json")
    if read_json(directory / "preregistration.json") != {
            "plan_sha256": digest(directory / "plan.json"), "source_sha256": plan["source_sha256"],
            "created_utc": plan["preregistration"]["created_utc"],
            "kind": "local hashed source and protocol snapshot", "independent_timestamp_registry": False}:
        raise ExpansionStudyError("local preregistration receipt differs from plan")
    if plan.get("source_sha256") != source_hashes():
        raise ExpansionStudyError("execution source changed after local preregistration")
    expected = set(SOURCE_FILES)
    snapshots = directory / "sources"
    if snapshots.is_symlink() or not snapshots.is_dir() or {p.name for p in snapshots.iterdir()} != expected:
        raise ExpansionStudyError("source snapshot inventory differs")
    for path in snapshots.iterdir():
        if path.is_symlink() or not path.is_file() or digest(path) != plan["source_sha256"][path.name]:
            raise ExpansionStudyError(f"source snapshot changed: {path.name}")
    if (plan.get("profiles") != list(PROFILES) or plan.get("players") != list(range(2, 11)) or
            plan.get("fields") != list(FIELDS) or plan.get("policies") != list(POLICIES) or
            plan.get("configurations") != _configuration_catalogue() or
            plan.get("counter_settings") != [list(setting) for setting in COUNTER_SETTINGS] or
            plan.get("confirmation_family_size") != 135 or plan.get("counter_family_size") != 6 or
            plan.get("max_turns") != 1000 or plan.get("strict_every_action") is not True or
            plan.get("raw_columns") != list(RAW_COLUMNS)):
        raise ExpansionStudyError("protocol structure differs from supported frozen design")
    fixed = {
        "schema_version": 1, "study": "Coup expansion strategy study",
        "deck_copies": {str(n): 3 if n <= 6 else 4 if n <= 8 else 5 for n in range(2, 11)},
        "opponents": OPPONENTS, "mixed_pool": list(POLICIES), "stages": list(STAGES),
        "seed_rule": "SHA256 ASCII coup-expansion-study-v1:profile:stage:players:field:block, big-endian integer",
        "lineup_rule": "identity 0 focal; mixed pool[(block+j)%8] for j=0..n-2, reverse on odd pool cycles; rotate every identity right by rotation",
        "decision_rng_rule": "engine domain-separated per participant identity, independent from environment/deck randomness",
        "selection_rule": "per profile/player count, rank mean screening win rate equally across five fields; top two; ties lexical policy ID",
        "counter_target_rule": "screening rank first per specified profile/player count",
        "counter_selection_rule": "highest search win rate excluding target; ties lexical policy ID",
        "inference": {"alpha": 0.05, "practical_threshold": 0.02,
                      "independent_unit": "complete rotation block",
                      "intervals": ["approximate Bonferroni normal", "conservative simultaneous Hoeffding"],
                      "draw_denominator": "all scheduled games", "no_confirmation_retuning": True},
    }
    if any(plan.get(key) != value for key, value in fixed.items()):
        raise ExpansionStudyError("frozen model, seed, selection or inference contract differs")
    expected_keys = set(fixed) | {"preregistration", "python", "source_sha256", "profiles", "players", "policies",
        "configurations", "fields", "blocks", "max_turns", "strict_every_action", "raw_columns",
        "confirmation_family_size", "counter_settings", "counter_family_size"}
    if set(plan) != expected_keys:
        raise ExpansionStudyError("global plan key inventory differs")
    registration = plan["preregistration"]
    if (not isinstance(registration, dict) or set(registration) != {
            "kind", "independent_timestamp_registry", "created_utc"} or
            registration.get("kind") != "local hashed source and protocol snapshot" or
            registration.get("independent_timestamp_registry") is not False):
        raise ExpansionStudyError("invalid local registration disclosure")
    if set(plan.get("blocks", {})) != set(STAGES):
        raise ExpansionStudyError("stage block inventory differs")
    for stage in STAGES:
        _bounds(plan["blocks"][stage], stage)
    return plan


def seed_for(profile, stage, players, field, block):
    if (profile not in PROFILES or stage not in STAGES or not 2 <= players <= 10 or
            not SAFE_NAME.fullmatch(field) or not 0 <= block < 100000):
        raise ExpansionStudyError("invalid seed coordinates")
    text = f"coup-expansion-study-v1:{profile}:{stage}:{players}:{field}:{block}"
    return int.from_bytes(hashlib.sha256(text.encode("ascii")).digest(), "big")


def roster(players, candidate, field, block, rotation):
    if candidate not in POLICIES or not 2 <= players <= 10 or not 0 <= rotation < players:
        raise ExpansionStudyError("invalid roster coordinate")
    if field in OPPONENTS:
        opponents = [OPPONENTS[field]] * (players - 1)
    elif field == "mixed":
        opponents = [POLICIES[(block + j) % len(POLICIES)] for j in range(players - 1)]
        if (block // len(POLICIES)) % 2:
            opponents.reverse()
    elif field.startswith("vs_") and field[3:] in POLICIES:
        opponents = [field[3:]] * (players - 1)
    else:
        raise ExpansionStudyError("unplanned opponent field")
    names, identities = [candidate] + opponents, list(range(players))
    if rotation:
        names = names[-rotation:] + names[:-rotation]
        identities = identities[-rotation:] + identities[:-rotation]
    if identities[rotation] != 0:
        raise ExpansionStudyError("focal identity attribution failed")
    return names, identities


def _job(profile, players, field, candidate, blocks):
    return {"profile": profile, "players": players, "field": field, "candidate": candidate, "blocks": blocks}


def _filename(job):
    if (job.get("profile") not in PROFILES or job.get("candidate") not in POLICIES or
            not 2 <= integer(job.get("players"), "players") <= 10 or
            not isinstance(job.get("field"), str) or not SAFE_NAME.fullmatch(job["field"])):
        raise ExpansionStudyError("unsafe job identity")
    return f"{job['profile']}-{job['players']}-{job['field']}-{job['candidate']}.csv.gz"


def _raw_rows(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ExpansionStudyError(f"regular raw file required: {path}")
    try:
        with gzip.open(path, "rt", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            if tuple(reader.fieldnames or ()) != RAW_COLUMNS:
                raise ExpansionStudyError("raw outcome schema differs")
            for row in reader:
                if set(row) != set(RAW_COLUMNS) or any(v is None for v in row.values()):
                    raise ExpansionStudyError("malformed raw row")
                yield row
    except (OSError, EOFError, UnicodeError) as exc:
        raise ExpansionStudyError(f"damaged compressed outcomes: {path}") from exc


def _summarize(rows, stage, job):
    n, count = job["players"], job["blocks"]
    rows = list(rows)
    for row in rows:
        if (row["profile"] != job["profile"] or row["stage"] != stage or
                integer(row["players"], "players") != n or row["field"] != job["field"] or
                row["candidate"] != job["candidate"] or
                integer(row["seed"], "seed") != seed_for(job["profile"], stage, n, job["field"], integer(row["block"], "block")) or
                not 1 <= integer(row["turns"], "turns") <= 1000 or
                (integer(row["draw"], "draw") == 1 and integer(row["turns"], "turns") != 1000)):
            raise ExpansionStudyError("raw coordinate, seed or turn cap differs from frozen job")
    games = panel(rows, n, [job["candidate"]], count)[job["candidate"]]
    wins, draws, turns = (sum(v[index] for v in games.values()) for index in (1, 2, 3))
    return {"profile": job["profile"], "stage": stage, "players": n, "field": job["field"],
            "candidate": job["candidate"], "blocks": count, "games": n * count,
            "wins": wins, "draws": draws, "win_rate": wins / (n * count), "mean_turns": turns / (n * count)}


def _run_job(directory, stage, job):
    from expansion_simulator import ExpansionGame
    directory = Path(directory)
    plan = _check_plan(directory)
    path = directory / stage / _filename(job)
    diagnostic = path.with_suffix(".diagnostics.json")
    if path.exists() or diagnostic.exists():
        if not path.exists() or not diagnostic.exists():
            raise ExpansionStudyError("partial job needs inspection before resuming")
        cached = read_json(diagnostic)
        summary = _summarize(_raw_rows(path), stage, job)
        if (cached.get("job") != job or cached.get("stage") != stage or
                cached.get("raw_sha256") != digest(path) or cached.get("summary") != summary):
            raise ExpansionStudyError("cached outcomes or summaries changed")
        return cached
    temporary = path.with_suffix(".part")
    if temporary.exists() or temporary.is_symlink():
        raise ExpansionStudyError("interrupted temporary job needs inspection")
    counts = Counter()
    wins = draws = turns = 0
    with temporary.open("xb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text:
                writer = csv.DictWriter(text, fieldnames=RAW_COLUMNS)
                writer.writeheader()
                for block in range(job["blocks"]):
                    seed = seed_for(job["profile"], stage, job["players"], job["field"], block)
                    for rotation in range(job["players"]):
                        names, identities = roster(job["players"], job["candidate"], job["field"], block, rotation)
                        game = ExpansionGame(job["players"], seed=seed, policies=names, profile=job["profile"],
                                             max_turns=plan["max_turns"], strict=True, record=False, identities=identities)
                        winner = game.run()
                        won, draw = int(winner == rotation), int(winner is None)
                        wins += won; draws += draw; turns += game.turn
                        counts.update(game.diagnostics)
                        writer.writerow(dict(zip(RAW_COLUMNS, (job["profile"], stage, job["players"], job["field"],
                            job["candidate"], block, rotation, seed, "" if draw else winner, rotation, won, draw, game.turn))))
    if source_hashes() != plan["source_sha256"]:
        raise ExpansionStudyError("execution source changed during job; preserve partial outcomes")
    temporary.replace(path)
    summary = {"profile": job["profile"], "stage": stage, "players": job["players"], "field": job["field"],
        "candidate": job["candidate"], "blocks": job["blocks"], "games": job["players"] * job["blocks"],
        "wins": wins, "draws": draws, "win_rate": wins / (job["players"] * job["blocks"]),
        "mean_turns": turns / (job["players"] * job["blocks"])}
    if _summarize(_raw_rows(path), stage, job) != summary:
        raise ExpansionStudyError("written outcomes disagree with execution counts")
    result = {"stage": stage, "job": job, "summary": summary, "raw_sha256": digest(path),
              "diagnostics": dict(sorted(counts.items()))}
    freeze_json(diagnostic, result)
    return result


def _screen_jobs(plan):
    return [_job(profile, n, field, policy, plan["blocks"]["screening"])
            for profile in PROFILES for n in range(2, 11) for field in FIELDS for policy in POLICIES]


def select_finalists(summaries):
    result = []
    for profile in PROFILES:
        for n in range(2, 11):
            subset = [row for row in summaries if row["profile"] == profile and row["players"] == n]
            if {(r["field"], r["candidate"]) for r in subset} != {(f, p) for f in FIELDS for p in POLICIES}:
                raise ExpansionStudyError("screening roster incomplete")
            # Every field has the same denominator at a fixed player count.
            totals = {p: sum(r["wins"] for r in subset if r["candidate"] == p) for p in POLICIES}
            ranking = sorted(POLICIES, key=lambda p: (-totals[p], p))
            result.append({"profile": profile, "players": n, "first": ranking[0], "second": ranking[1],
                           "screening_rank": ranking})
    return {"finalists": result}


def _confirmation_jobs(plan, selection):
    return [_job(row["profile"], row["players"], field, row[key], plan["blocks"]["confirmation"])
            for row in selection["finalists"] for field in FIELDS for key in ("first", "second")]


def _counter_search_jobs(plan, selection):
    ranks = {(r["profile"], r["players"]): r for r in selection["finalists"]}
    return [_job(profile, n, "vs_" + ranks[profile, n]["first"], candidate, plan["blocks"]["counter_search"])
            for profile, n in COUNTER_SETTINGS for candidate in POLICIES]


def select_counters(summaries, selection):
    ranks = {(r["profile"], r["players"]): r for r in selection["finalists"]}
    result = []
    for profile, n in COUNTER_SETTINGS:
        target = ranks[profile, n]["first"]
        field = "vs_" + target
        rows = [r for r in summaries if (r["profile"], r["players"], r["field"]) == (profile, n, field)]
        if {r["candidate"] for r in rows} != set(POLICIES):
            raise ExpansionStudyError("counter search roster incomplete")
        contenders = sorted((r for r in rows if r["candidate"] != target), key=lambda r: (-r["wins"], r["candidate"]))
        result.append({"profile": profile, "players": n, "field": field,
                       "first": contenders[0]["candidate"], "second": target})
    return {"pairs": result}


def _counter_jobs(plan, selection):
    return [_job(r["profile"], r["players"], r["field"], r[key], plan["blocks"]["counters"])
            for r in selection["pairs"] for key in ("first", "second")]


def _write_csv(path, rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=SUMMARY_COLUMNS)
    writer.writeheader(); writer.writerows(rows)
    content = output.getvalue().encode("utf-8")
    path = Path(path)
    if path.exists():
        if path.is_symlink() or path.read_bytes() != content:
            raise ExpansionStudyError("frozen summary differs")
    else:
        path.write_bytes(content)


def _run_stage(directory, stage, jobs, workers):
    directory = Path(directory)
    plan = _check_plan(directory)
    stage_dir = directory / stage
    if stage_dir.is_symlink():
        raise ExpansionStudyError("stage directory may not be symlinked")
    stage_dir.mkdir(exist_ok=True)
    stage_plan = {"stage": stage, "global_plan_sha256": digest(directory / "plan.json"),
                  "source_sha256": plan["source_sha256"], "jobs": jobs}
    freeze_json(stage_dir / "plan.json", stage_plan)
    started = time.monotonic()
    print(f"{stage}: {len(jobs)} jobs, {sum(j['players'] * j['blocks'] for j in jobs):,} planned games", flush=True)
    def progress(completed):
        if completed == len(jobs) or completed % max(1, len(jobs) // 10) == 0:
            print(f"{stage}: {completed}/{len(jobs)} jobs complete, {time.monotonic()-started:.1f}s", flush=True)
    if workers == 1:
        records = []
        for job in jobs:
            records.append(_run_job(directory, stage, job))
            progress(len(records))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_run_job, str(directory), stage, job) for job in jobs]
            records = []
            for future in as_completed(futures):
                records.append(future.result())
                progress(len(records))
    by_file = {_filename(r["job"]): r for r in records}
    rows = [by_file[_filename(job)]["summary"] for job in jobs]
    _write_csv(stage_dir / "summaries.csv", rows)
    expected = {"plan.json", "summaries.csv"} | {_filename(job) for job in jobs} | {
        str(Path(_filename(job)).with_suffix(".diagnostics.json")) for job in jobs}
    actual = {p.name for p in stage_dir.iterdir() if p.name != "manifest.json"}
    if actual != expected or any(p.is_symlink() or not p.is_file() for p in stage_dir.iterdir()):
        raise ExpansionStudyError("stage inventory drift")
    freeze_json(stage_dir / "manifest.json", {"stage": stage, "plan_sha256": digest(stage_dir / "plan.json"),
        "global_plan_sha256": digest(directory / "plan.json"), "source_sha256": plan["source_sha256"],
        "scheduled_games": sum(r["games"] for r in rows), "files": {name: digest(stage_dir / name) for name in sorted(expected)}})
    return audit_stage(directory, stage, jobs)["summaries"]


def audit_stage(directory, stage, expected_jobs):
    directory = Path(directory)
    plan = _check_plan(directory)
    stage_dir = directory / stage
    if stage_dir.is_symlink():
        raise ExpansionStudyError("symlinked stage")
    stage_plan = read_json(stage_dir / "plan.json")
    if stage_plan != {"stage": stage, "global_plan_sha256": digest(directory / "plan.json"),
                      "source_sha256": plan["source_sha256"], "jobs": expected_jobs}:
        raise ExpansionStudyError("stage plan differs from independently reconstructed selection")
    expected = {"plan.json", "summaries.csv"} | {_filename(job) for job in expected_jobs} | {
        str(Path(_filename(job)).with_suffix(".diagnostics.json")) for job in expected_jobs}
    if len({_filename(job) for job in expected_jobs}) != len(expected_jobs):
        raise ExpansionStudyError("duplicate planned job")
    if {p.name for p in stage_dir.iterdir()} != expected | {"manifest.json"}:
        raise ExpansionStudyError("stage file inventory differs")
    if any(p.is_symlink() or not p.is_file() for p in stage_dir.iterdir()):
        raise ExpansionStudyError("stage contains nonregular files")
    manifest = read_json(stage_dir / "manifest.json")
    exact_manifest = {"stage": stage, "plan_sha256": digest(stage_dir / "plan.json"),
        "global_plan_sha256": digest(directory / "plan.json"), "source_sha256": plan["source_sha256"],
        "scheduled_games": sum(j["players"] * j["blocks"] for j in expected_jobs),
        "files": {name: digest(stage_dir / name) for name in sorted(expected)}}
    if manifest != exact_manifest:
        raise ExpansionStudyError("stage manifest or publication bytes changed")
    summaries, diagnostics = [], Counter()
    for job in expected_jobs:
        path = stage_dir / _filename(job)
        rows = list(_raw_rows(path))
        summary = _summarize(rows, stage, job)
        record = read_json(path.with_suffix(".diagnostics.json"))
        if (set(record) != {"stage", "job", "summary", "raw_sha256", "diagnostics"} or
                record["stage"] != stage or record["job"] != job or record["summary"] != summary or
                record["raw_sha256"] != digest(path) or not isinstance(record["diagnostics"], dict)):
            raise ExpansionStudyError("diagnostic and raw outcomes disagree")
        for name, count in record["diagnostics"].items():
            if not isinstance(name, str) or not name:
                raise ExpansionStudyError("invalid diagnostic key")
            diagnostics[name] += integer(count, "diagnostic count")
        summaries.append(summary)
    with (stage_dir / "summaries.csv").open(newline="") as file:
        reader = csv.DictReader(file)
        if tuple(reader.fieldnames or ()) != SUMMARY_COLUMNS:
            raise ExpansionStudyError("summary schema differs")
        saved = list(reader)
    if len(saved) != len(summaries) or any({k: str(v) for k, v in expected.items()} != actual
                                          for expected, actual in zip(summaries, saved)):
        raise ExpansionStudyError("summary rows differ from raw outcomes")
    return {"stage": stage, "games": sum(r["games"] for r in summaries),
            "draws": sum(r["draws"] for r in summaries), "jobs": len(summaries),
            "summaries": summaries,
            "diagnostics": dict(sorted(diagnostics.items())), "manifest_sha256": digest(stage_dir / "manifest.json")}


def run_study(directory=DEFAULT_STUDY, *, workers=4, stop_after=None):
    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 8:
        raise ExpansionStudyError("workers must be between one and eight")
    if stop_after is not None and stop_after not in STAGES:
        raise ExpansionStudyError("unknown stopping stage")
    directory = Path(directory)
    plan = _check_plan(directory)
    screen = _run_stage(directory, "screening", _screen_jobs(plan), workers)
    selection = select_finalists(screen)
    freeze_json(directory / "selection.json", selection)
    if stop_after == "screening":
        return selection
    _run_stage(directory, "confirmation", _confirmation_jobs(plan, selection), workers)
    if stop_after == "confirmation":
        return selection
    search = _run_stage(directory, "counter_search", _counter_search_jobs(plan, selection), workers)
    counters = select_counters(search, selection)
    freeze_json(directory / "counter_selection.json", counters)
    if stop_after == "counter_search":
        return counters
    _run_stage(directory, "counters", _counter_jobs(plan, counters), workers)
    return verify_study(directory, write=True)


def _compare_saved(saved, actual, path=()):
    """Accept only tiny derived-bound libm rounding, never changed evidence."""
    allowed = {"normal_family_lower", "normal_family_upper", "conservative_family_lower", "conservative_family_upper"}
    if type(saved) is not type(actual):
        raise ExpansionStudyError(f"findings type differs: {path}")
    if isinstance(actual, dict):
        if saved.keys() != actual.keys():
            raise ExpansionStudyError(f"findings keys differ: {path}")
        for key in actual:
            _compare_saved(saved[key], actual[key], path + (key,))
    elif isinstance(actual, list):
        if len(saved) != len(actual):
            raise ExpansionStudyError(f"findings length differs: {path}")
        for index, item in enumerate(actual):
            _compare_saved(saved[index], item, path + (index,))
    elif isinstance(actual, float):
        if not math.isfinite(saved) or not math.isfinite(actual):
            raise ExpansionStudyError("nonfinite findings")
        if saved != actual and not (len(path) == 3 and path[0] in ("confirmation_pairs", "counters") and
                path[-1] in allowed and saved != 0 and actual != 0 and (saved > 0) == (actual > 0) and abs(saved - actual) <= 1e-14):
            raise ExpansionStudyError(f"findings number differs: {path}")
    elif saved != actual:
        raise ExpansionStudyError(f"findings value differs: {path}")


def markdown_findings(result):
    lines = ["# Coup expansion strategy findings", "",
        "These results concern the tested computer policies and opponent fields. They do not establish optimal human play.", "",
        f"{result['total_games']:,} scheduled games; {result['total_draws']:,} capped games counted in every win-rate denominator.", "",
        "## Equal-field confirmation results", "",
        "Each row compares the two policies selected on earlier screening, averaged equally across five programmed opponent fields. These averages are descriptive.", "",
        "| Expansion | Players | Policy | Wins / games | Equal-field win rate | Worst field |",
        "| --- | ---: | --- | ---: | ---: | --- |"]
    for row in result["recommendations"]:
        lines.append(f"| {row['profile']} | {row['players']} | {row['candidate']} | {row['wins']} / {row['games']} | {row['equal_field_mean']:.2%} | {row['worst_field']} ({row['worst_rate']:.2%}) |")
    lines += ["", "## Paired evidence", "",
        "The 135 confirmation contrasts use matched complete rotation blocks. Normal simultaneous intervals are approximate; Hoeffding intervals are conservative. A positive bound supports a modeled advantage; a lower bound above two percentage points supports a practical advantage under that method.", "",
        "| Expansion | Players | Field | First vs second | Difference | Approximate interval | Conservative interval |",
        "| --- | ---: | --- | --- | ---: | --- | --- |"]
    for r in result["confirmation_pairs"]:
        lines.append(f"| {r['profile']} | {r['players']} | {r['field']} | {r['first']} vs {r['second']} | {100*r['difference']:+.2f} pp | {100*r['normal_family_lower']:+.2f} to {100*r['normal_family_upper']:+.2f} pp | {100*r['conservative_family_lower']:+.2f} to {100*r['conservative_family_upper']:+.2f} pp |")
    lines += ["", "## Targeted counters", "",
        "Targets came from screening; counters were selected on separate search games and tested on fresh games against copies of the target. Each paired reference is target self-play.", "",
        "| Expansion | Players | Counter vs target | Counter win rate | Difference | Conservative interval |",
        "| --- | ---: | --- | ---: | ---: | --- |"]
    for r in result["counters"]:
        lines.append(f"| {r['profile']} | {r['players']} | {r['first']} vs {r['second']} | {r['first_rate']:.2%} | {100*r['difference']:+.2f} pp | {100*r['conservative_family_lower']:+.2f} to {100*r['conservative_family_upper']:+.2f} pp |")
    lines += ["", "## Scope", "",
        "The protocol and execution sources were frozen in a local hashed snapshot before outcomes. This is not independent timestamp registration. The model omits negotiation, persuasion and cross-game adaptation. Opponent fields are scenarios, not an estimate of human populations. Public mechanism counters are descriptive. The two confirmed policies per player count cannot establish superiority over every screened or untested strategy.", ""]
    return "\n".join(lines)


def _pair_rows(directory, stage, profile, players, field, first, second):
    # Bound verification memory to two candidate jobs, including at ten players.
    return [row for candidate in (first, second)
            for row in _raw_rows(Path(directory) / stage / _filename(
                _job(profile, players, field, candidate, 0)))]


def verify_study(directory=DEFAULT_STUDY, *, write=False):
    """Reconstruct every stage and selection from raw outcomes, without playing games."""
    if not __debug__:
        raise ExpansionStudyError("optimized Python is not allowed for evidence verification")
    directory = Path(directory)
    if directory.is_symlink():
        raise ExpansionStudyError("symlinked study directory")
    plan = _check_plan(directory)
    required = {"plan.json", "preregistration.json", "sources", "selection.json", "counter_selection.json", *STAGES}
    optional = {"findings.json", "FINDINGS.md", "replay-audit.json"}
    actual = {path.name for path in directory.iterdir()}
    if not required <= actual or not actual <= required | optional:
        raise ExpansionStudyError("study root inventory differs")
    for path in directory.iterdir():
        should_be_directory = path.name in {"sources", *STAGES}
        if path.is_symlink() or (not path.is_dir() if should_be_directory else not path.is_file()):
            raise ExpansionStudyError("study root contains linked or nonregular entries")
    screening = audit_stage(directory, "screening", _screen_jobs(plan))
    selection = select_finalists(screening["summaries"])
    if read_json(directory / "selection.json") != selection:
        raise ExpansionStudyError("confirmation selection differs from screening")
    confirmation = audit_stage(directory, "confirmation", _confirmation_jobs(plan, selection))
    search = audit_stage(directory, "counter_search", _counter_search_jobs(plan, selection))
    counter_selection = select_counters(search["summaries"], selection)
    if read_json(directory / "counter_selection.json") != counter_selection:
        raise ExpansionStudyError("counter selection differs from search")
    counters = audit_stage(directory, "counters", _counter_jobs(plan, counter_selection))
    stages = (screening, confirmation, search, counters)
    pairs = []
    for row in selection["finalists"]:
        for field in FIELDS:
            result = paired_compare(_pair_rows(directory, "confirmation", row["profile"], row["players"], field, row["first"], row["second"]),
                row["players"], row["first"], row["second"], plan["blocks"]["confirmation"],
                plan["confirmation_family_size"], alpha=plan["inference"]["alpha"],
                practical_threshold=plan["inference"]["practical_threshold"])
            result.update(profile=row["profile"], field=field)
            pairs.append(result)
    counter_pairs = []
    for row in counter_selection["pairs"]:
        result = paired_compare(_pair_rows(directory, "counters", row["profile"], row["players"], row["field"], row["first"], row["second"]),
            row["players"], row["first"], row["second"], plan["blocks"]["counters"], plan["counter_family_size"],
            alpha=plan["inference"]["alpha"], practical_threshold=plan["inference"]["practical_threshold"])
        result.update(profile=row["profile"], field=row["field"])
        counter_pairs.append(result)
    recommendations = []
    for selected in selection["finalists"]:
        profile, n = selected["profile"], selected["players"]
        for candidate in (selected["first"], selected["second"]):
            rows = [r for r in confirmation["summaries"] if (r["profile"], r["players"], r["candidate"]) == (profile, n, candidate)]
            wins, games = sum(r["wins"] for r in rows), sum(r["games"] for r in rows)
            worst = min(rows, key=lambda r: (r["wins"], r["field"]))
            recommendations.append({"profile": profile, "players": n, "candidate": candidate,
                "wins": wins, "games": games, "equal_field_mean": wins / games,
                "worst_field": worst["field"], "worst_rate": worst["win_rate"],
                "draws": sum(r["draws"] for r in rows), "screening_position": 1 if candidate == selected["first"] else 2})
    result = {"schema_version": 1, "plan_sha256": digest(directory / "plan.json"),
        "source_sha256": plan["source_sha256"], "preregistration": plan["preregistration"],
        "total_games": sum(s["games"] for s in stages), "total_draws": sum(s["draws"] for s in stages),
        "stages": [{k: s[k] for k in ("stage", "games", "draws", "jobs", "manifest_sha256")} for s in stages],
        "screening": screening["summaries"], "confirmation": confirmation["summaries"],
        "confirmation_pairs": pairs, "counters": counter_pairs, "recommendations": recommendations,
        "diagnostics": {s["stage"]: s["diagnostics"] for s in stages},
        "limitations": ["finite computer-policy population", "no human negotiation or cross-game learning",
                        "two screening-selected policies confirmed per profile/player count",
                        "approximate intervals and conservative bounds reported separately"]}
    findings = directory / "findings.json"
    if findings.exists():
        saved = read_json(findings)
        _compare_saved(saved, result)
        result = saved
        markdown_path = directory / "FINDINGS.md"
        if markdown_path.is_symlink() or not markdown_path.is_file() or markdown_path.read_text() != markdown_findings(result):
            raise ExpansionStudyError("findings Markdown differs from audited evidence")
    elif write:
        freeze_path = directory / "FINDINGS.md"
        if freeze_path.exists() or freeze_path.is_symlink():
            raise ExpansionStudyError("existing Markdown without findings needs inspection")
        freeze_json(findings, result)
        freeze_path.write_text(markdown_findings(result))
    else:
        raise ExpansionStudyError("saved findings are missing; generate them explicitly after completed outcomes")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--screen-blocks", type=int)
    parser.add_argument("--confirmation-blocks", type=int)
    parser.add_argument("--counter-search-blocks", type=int)
    parser.add_argument("--counter-blocks", type=int)
    parser.add_argument("--freeze-only", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--stop-after", choices=STAGES)
    args = parser.parse_args()
    if args.verify:
        findings = verify_study(args.output_dir)
        print(f"Verified {findings['total_games']:,} scheduled expansion games")
        return
    existing = read_json(args.output_dir / "plan.json") if (args.output_dir / "plan.json").exists() else {}
    frozen = existing.get("blocks", {})
    freeze_plan(args.output_dir,
                screen_blocks=args.screen_blocks if args.screen_blocks is not None else frozen.get("screening", 32),
                confirmation_blocks=args.confirmation_blocks if args.confirmation_blocks is not None else frozen.get("confirmation", 1000),
                counter_search_blocks=args.counter_search_blocks if args.counter_search_blocks is not None else frozen.get("counter_search", 32),
                counter_blocks=args.counter_blocks if args.counter_blocks is not None else frozen.get("counters", 1000))
    if args.freeze_only:
        print(f"Locally frozen protocol and source snapshots: {args.output_dir}")
        return
    run_study(args.output_dir, workers=args.workers, stop_after=args.stop_after)


if __name__ == "__main__":
    main()
