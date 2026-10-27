"""Independent raw-outcome and strict replay audit for the expansion study.

The runner and its schedule helpers are deliberately not imported.  The audit
checks every raw coordinate and aggregate, then replays the first, midpoint and
last complete blocks at every physical seat.  Replay uses the expansion rules
engine, so the separately authored transition tests remain a distinct rules
check rather than being implied by this receipt.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
DEFAULT_STUDY = ROOT / "research_results" / "2026-10-18-expansion"
PROFILES = ("inquisitor", "reformation", "combined")
PLAYERS = tuple(range(2, 11))
POLICIES = ("honest", "bluff", "skeptic", "treasury", "shield", "converter", "information", "balanced")
FIELDS = ("honest", "bluffing", "skeptical", "adaptive", "mixed")
OPPONENTS = {"honest": "honest", "bluffing": "bluff", "skeptical": "skeptic", "adaptive": "balanced"}
STAGES = ("screening", "confirmation", "counter_search", "counters")
COUNTER_SETTINGS = (("inquisitor", 2), ("inquisitor", 6), ("reformation", 4),
                    ("reformation", 10), ("combined", 4), ("combined", 10))
SOURCE_FILES = {"expansion_simulator.py", "expansion_policies.py", "expansion_study.py",
                "expansion_statistics.py", "test_expansion_study.py", "test_expansion_simulator.py",
                "audit_expansion_research.py", "test_expansion_audit.py"}
RAW_COLUMNS = ("profile", "stage", "players", "field", "candidate", "block", "rotation",
               "seed", "winner", "focal_seat", "won", "draw", "turns")
SUMMARY_COLUMNS = ("profile", "stage", "players", "field", "candidate", "blocks", "games",
                   "wins", "draws", "win_rate", "mean_turns")
SEED_RULE = "SHA256 ASCII coup-expansion-study-v1:profile:stage:players:field:block, big-endian integer"
LINEUP_RULE = "identity 0 focal; mixed pool[(block+j)%8] for j=0..n-2, reverse on odd pool cycles; rotate every identity right by rotation"
SAFE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ExpansionAuditError(ValueError):
    """Frozen evidence or a fresh strict replay disagrees with the protocol."""


def sha256(path: Path) -> str:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ExpansionAuditError(f"Missing or linked audit input: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ExpansionAuditError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path):
    path = Path(path)
    sha256(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"),
                           object_pairs_hook=_unique_object,
                           parse_constant=lambda item: _reject(f"Nonfinite JSON value: {item}"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExpansionAuditError(f"Unreadable JSON input: {path}") from exc
    if path.read_bytes() != json_bytes(value):
        raise ExpansionAuditError(f"Noncanonical JSON input: {path}")
    return value


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _reject(message):
    raise ExpansionAuditError(message)


def integer(value, name, *, minimum=0, maximum=None):
    if isinstance(value, bool):
        raise ExpansionAuditError(f"Invalid integer {name}")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and value.isascii() and value.isdecimal():
        number = int(value)
        if str(number) != value:
            raise ExpansionAuditError(f"Noncanonical integer {name}")
    else:
        raise ExpansionAuditError(f"Invalid integer {name}")
    if number < minimum or maximum is not None and number > maximum:
        raise ExpansionAuditError(f"Out-of-range integer {name}")
    return number


def checked_name(value, kind="name"):
    if not isinstance(value, str) or not SAFE_NAME.fullmatch(value):
        raise ExpansionAuditError(f"Unsafe {kind}: {value!r}")
    return value


def sample_blocks(blocks: int) -> list[int]:
    integer(blocks, "blocks", minimum=1)
    return sorted({0, blocks // 2, blocks - 1})


def verify_plan(directory: Path, source_root: Path) -> dict:
    if directory.is_symlink() or not directory.is_dir():
        raise ExpansionAuditError("Study must be a regular directory")
    plan = read_json(directory / "plan.json")
    fixed = {"schema_version": 1, "profiles": list(PROFILES), "players": list(PLAYERS),
             "policies": list(POLICIES), "fields": list(FIELDS), "opponents": OPPONENTS,
             "mixed_pool": list(POLICIES), "stages": list(STAGES), "seed_rule": SEED_RULE,
             "lineup_rule": LINEUP_RULE, "raw_columns": list(RAW_COLUMNS),
             "max_turns": 1000, "strict_every_action": True, "confirmation_family_size": 135,
             "counter_family_size": 6, "counter_settings": [list(c) for c in COUNTER_SETTINGS],
             "selection_rule": "per profile/player count, rank mean screening win rate equally across five fields; top two; ties lexical policy ID",
             "counter_target_rule": "screening rank first per specified profile/player count",
             "counter_selection_rule": "highest search win rate excluding target; ties lexical policy ID",
             "decision_rng_rule": "engine domain-separated per participant identity, independent from environment/deck randomness",
             "deck_copies": {str(n): 3 if n <= 6 else 4 if n <= 8 else 5 for n in PLAYERS}}
    for key, expected in fixed.items():
        if type(plan.get(key)) is not type(expected) or plan[key] != expected:
            raise ExpansionAuditError(f"Unsupported frozen protocol: {key}")
    if set(plan.get("blocks", {})) != set(STAGES):
        raise ExpansionAuditError("Unexpected stage block inventory")
    for stage in STAGES:
        integer(plan["blocks"][stage], stage, minimum=2, maximum=100000)
    if not isinstance(plan.get("configurations"), dict) or set(plan["configurations"]) != set(POLICIES):
        raise ExpansionAuditError("Incomplete policy configuration catalogue")
    inference = {"alpha": 0.05, "practical_threshold": 0.02,
                 "independent_unit": "complete rotation block",
                 "intervals": ["approximate Bonferroni normal", "conservative simultaneous Hoeffding"],
                 "draw_denominator": "all scheduled games", "no_confirmation_retuning": True}
    if plan.get("inference") != inference:
        raise ExpansionAuditError("Unsupported frozen inference settings")
    preregistration = plan.get("preregistration", {})
    if (preregistration.get("kind") != "local hashed source and protocol snapshot" or
            preregistration.get("independent_timestamp_registry") is not False or
            not isinstance(preregistration.get("created_utc"), str)):
        raise ExpansionAuditError("Invalid local preregistration disclosure")
    receipt = {"plan_sha256": sha256(directory / "plan.json"),
               "source_sha256": plan.get("source_sha256"),
               "created_utc": preregistration["created_utc"],
               "kind": "local hashed source and protocol snapshot",
               "independent_timestamp_registry": False}
    if read_json(directory / "preregistration.json") != receipt:
        raise ExpansionAuditError("Preregistration receipt differs from frozen plan")
    sources = plan.get("source_sha256")
    if not isinstance(sources, dict) or set(sources) != SOURCE_FILES:
        raise ExpansionAuditError("Incomplete frozen source inventory")
    snapshots = directory / "sources"
    if snapshots.is_symlink() or not snapshots.is_dir() or {p.name for p in snapshots.iterdir()} != SOURCE_FILES:
        raise ExpansionAuditError("Source snapshot inventory drift")
    for name, expected in sources.items():
        if not isinstance(expected, str) or not SHA256.fullmatch(expected):
            raise ExpansionAuditError(f"Invalid source hash: {name}")
        if sha256(source_root / name) != expected or sha256(snapshots / name) != expected:
            raise ExpansionAuditError(f"Frozen live source or snapshot changed: {name}")
    return plan


def seed_for(profile: str, stage: str, players: int, field: str, block: int) -> int:
    if profile not in PROFILES or stage not in STAGES:
        raise ExpansionAuditError("Unknown seed namespace")
    integer(players, "players", minimum=2, maximum=10)
    integer(block, "block", maximum=99999)
    checked_name(field, "field")
    coordinate = ":".join(("coup-expansion-study-v1", profile, stage, str(players), field, str(block)))
    return int(hashlib.sha256(coordinate.encode("ascii")).hexdigest(), 16)


def lineup(players: int, candidate: str, field: str, block: int, rotation: int):
    integer(players, "players", minimum=2, maximum=10)
    integer(block, "block", maximum=99999)
    integer(rotation, "rotation", maximum=players - 1)
    if candidate not in POLICIES:
        raise ExpansionAuditError("Unknown focal policy")
    if field in OPPONENTS:
        opposition = [OPPONENTS[field] for _ in range(players - 1)]
    elif field == "mixed":
        opposition = [POLICIES[(block + identity - 1) % 8] for identity in range(1, players)]
        if block // 8 % 2:
            opposition = opposition[::-1]
    elif field.startswith("vs_") and field[3:] in POLICIES:
        opposition = [field[3:]] * (players - 1)
    else:
        raise ExpansionAuditError("Unknown opponent field")
    names, identities = [None] * players, [None] * players
    for identity, name in enumerate((candidate, *opposition)):
        seat = (identity + rotation) % players
        names[seat], identities[seat] = name, identity
    return names, identities


def job(profile, players, field, candidate, blocks):
    seed_for(profile, "screening", players, field, 0)
    lineup(players, candidate, field, 0, 0)
    integer(blocks, "blocks", minimum=2, maximum=100000)
    return {"profile": profile, "players": players, "field": field, "candidate": candidate, "blocks": blocks}


def filename(item: dict) -> str:
    job(**item)
    return f"{item['profile']}-{item['players']}-{item['field']}-{item['candidate']}.csv.gz"


def read_raw(path: Path, stage: str, item: dict, expected_hash: str):
    """Count all outcomes independently and retain only the complete replay sample."""
    if sha256(path) != expected_hash:
        raise ExpansionAuditError(f"Raw hash mismatch: {path}")
    players, blocks = item["players"], item["blocks"]
    chosen, samples, seen = set(sample_blocks(blocks)), {}, set()
    wins = draws = turns = 0
    try:
        with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != RAW_COLUMNS:
                raise ExpansionAuditError("Raw columns differ from frozen schema")
            for row in reader:
                if set(row) != set(RAW_COLUMNS) or any(value is None for value in row.values()):
                    raise ExpansionAuditError("Malformed raw row")
                expected = (item["profile"], stage, str(players), item["field"], item["candidate"])
                if tuple(row[name] for name in RAW_COLUMNS[:5]) != expected:
                    raise ExpansionAuditError("Raw row belongs to another job")
                block = integer(row["block"], "block", maximum=blocks - 1)
                rotation = integer(row["rotation"], "rotation", maximum=players - 1)
                coordinate = block, rotation
                if coordinate in seen:
                    raise ExpansionAuditError("Duplicate raw game")
                seen.add(coordinate)
                focal = integer(row["focal_seat"], "focal_seat", maximum=players - 1)
                winner = None if row["winner"] == "" else integer(row["winner"], "winner", maximum=players - 1)
                won = integer(row["won"], "won", maximum=1)
                draw = integer(row["draw"], "draw", maximum=1)
                turn = integer(row["turns"], "turns", minimum=1, maximum=1000)
                seed = integer(row["seed"], "seed")
                if (focal != rotation or won != int(winner == focal) or draw != int(winner is None) or
                        draw and turn != 1000 or
                        seed != seed_for(item["profile"], stage, players, item["field"], block)):
                    raise ExpansionAuditError("Invalid focal attribution, seed or outcome flags")
                wins += won
                draws += draw
                turns += turn
                if block in chosen:
                    samples[coordinate] = {"seed": seed, "winner": winner, "turns": turn}
    except (OSError, EOFError, UnicodeError, csv.Error) as exc:
        raise ExpansionAuditError(f"Unreadable compressed raw outcomes: {path}") from exc
    if len(seen) != players * blocks or len(samples) != len(chosen) * players:
        raise ExpansionAuditError("Incomplete raw rotation panel")
    if sha256(path) != expected_hash:
        raise ExpansionAuditError("Raw file changed during audit")
    games = players * blocks
    summary = dict(profile=item["profile"], stage=stage, players=players, field=item["field"],
                   candidate=item["candidate"], blocks=blocks, games=games, wins=wins, draws=draws,
                   win_rate=wins / games, mean_turns=turns / games)
    return summary, samples


def audit_stage(directory, plan, stage, jobs, game_class):
    stage_dir = directory / stage
    if stage_dir.is_symlink() or not stage_dir.is_dir():
        raise ExpansionAuditError(f"Missing or linked stage: {stage}")
    global_hash = sha256(directory / "plan.json")
    expected_plan = {"stage": stage, "global_plan_sha256": global_hash,
                     "source_sha256": plan["source_sha256"], "jobs": jobs}
    if read_json(stage_dir / "plan.json") != expected_plan:
        raise ExpansionAuditError("Stage jobs differ from independently reconstructed schedule")
    names = [filename(item) for item in jobs]
    if len(set(names)) != len(names):
        raise ExpansionAuditError("Duplicate scheduled job")
    expected_files = {"plan.json", "summaries.csv", *names,
                      *(str(Path(name).with_suffix(".diagnostics.json")) for name in names)}
    if {path.name for path in stage_dir.iterdir()} != expected_files | {"manifest.json"}:
        raise ExpansionAuditError("Frozen stage inventory drift")
    for path in stage_dir.iterdir():
        sha256(path)
    manifest = read_json(stage_dir / "manifest.json")
    expected_manifest = {"stage": stage, "global_plan_sha256": global_hash,
                         "source_sha256": plan["source_sha256"],
                         "plan_sha256": sha256(stage_dir / "plan.json"),
                         "scheduled_games": sum(j["players"] * j["blocks"] for j in jobs),
                         "files": {name: sha256(stage_dir / name) for name in sorted(expected_files)}}
    if manifest != expected_manifest:
        raise ExpansionAuditError("Stage manifest differs from exact file bytes")
    summaries, replayed, replay_digest = [], 0, hashlib.sha256()
    for item, name in zip(jobs, names):
        summary, samples = read_raw(stage_dir / name, stage, item, manifest["files"][name])
        diagnostic = read_json((stage_dir / name).with_suffix(".diagnostics.json"))
        if (set(diagnostic) != {"stage", "job", "summary", "raw_sha256", "diagnostics"} or
                diagnostic["stage"] != stage or diagnostic["job"] != item or
                diagnostic["summary"] != summary or diagnostic["raw_sha256"] != manifest["files"][name] or
                not isinstance(diagnostic["diagnostics"], dict)):
            raise ExpansionAuditError("Cached diagnostic summary differs from raw outcomes")
        for label, count in diagnostic["diagnostics"].items():
            if not isinstance(label, str) or not label:
                raise ExpansionAuditError("Invalid mechanism diagnostic label")
            integer(count, "diagnostic count")
        summaries.append(summary)
        for (block, rotation), row in sorted(samples.items()):
            names_at_seats, identities = lineup(item["players"], item["candidate"], item["field"], block, rotation)
            trial = game_class(item["players"], seed=row["seed"], policies=names_at_seats,
                               profile=item["profile"], identities=identities,
                               max_turns=1000, strict=True, record=False)
            winner = trial.run()
            trial.check_invariants()
            if winner != row["winner"] or trial.turn != row["turns"]:
                raise ExpansionAuditError(f"Strict replay disagrees: {stage}/{name}, block {block}, rotation {rotation}")
            winner_identity = None if winner is None else identities[winner]
            outcome = [stage, item["profile"], item["players"], item["field"], item["candidate"],
                       block, rotation, row["seed"], winner_identity, trial.turn]
            replay_digest.update(json.dumps(outcome, separators=(",", ":")).encode("ascii") + b"\n")
            replayed += 1
    with (stage_dir / "summaries.csv").open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != SUMMARY_COLUMNS:
            raise ExpansionAuditError("Summary CSV schema differs")
        if list(reader) != [{key: str(row[key]) for key in SUMMARY_COLUMNS} for row in summaries]:
            raise ExpansionAuditError("Saved summaries differ from independently counted raw outcomes")
    if read_json(stage_dir / "manifest.json") != expected_manifest:
        raise ExpansionAuditError("Stage manifest changed during replay")
    if any(sha256(stage_dir / name) != digest for name, digest in expected_manifest["files"].items()):
        raise ExpansionAuditError("Stage bytes changed during replay")
    return {"stage": stage, "jobs": len(jobs), "raw_games": sum(r["games"] for r in summaries),
            "draws": sum(r["draws"] for r in summaries), "replayed_games": replayed,
            "stage_plan_sha256": sha256(stage_dir / "plan.json"),
            "stage_manifest_sha256": sha256(stage_dir / "manifest.json"),
            "replay_identity_outcomes_sha256": replay_digest.hexdigest()}, summaries


def select_finalists(summaries):
    ranks = []
    for profile in PROFILES:
        for n in PLAYERS:
            cells = [r for r in summaries if r["profile"] == profile and r["players"] == n]
            if (len(cells) != len(FIELDS) * len(POLICIES) or
                    {(r["field"], r["candidate"]) for r in cells} != {(f, p) for f in FIELDS for p in POLICIES}):
                raise ExpansionAuditError("Incomplete screening cells for selection")
            scores = {p: sum(r["wins"] for r in cells if r["candidate"] == p) for p in POLICIES}
            ordering = sorted(scores, key=lambda p: (-scores[p], p))
            ranks.append({"profile": profile, "players": n, "first": ordering[0], "second": ordering[1],
                          "screening_rank": ordering})
    return {"finalists": ranks}


def select_counters(summaries, selection):
    selected = {(r["profile"], r["players"]): r["first"] for r in selection["finalists"]}
    pairs = []
    for profile, n in COUNTER_SETTINGS:
        target = selected[profile, n]
        field = "vs_" + target
        cells = [r for r in summaries if (r["profile"], r["players"], r["field"]) == (profile, n, field)]
        if len(cells) != len(POLICIES) or {r["candidate"] for r in cells} != set(POLICIES):
            raise ExpansionAuditError("Incomplete counter search cells")
        counter = min((r for r in cells if r["candidate"] != target), key=lambda r: (-r["wins"], r["candidate"]))
        pairs.append({"profile": profile, "players": n, "field": field, "first": counter["candidate"], "second": target})
    return {"pairs": pairs}


def audit(directory=DEFAULT_STUDY, *, source_root=ROOT, game_class=None, stages=STAGES):
    if not __debug__:
        raise ExpansionAuditError("Optimized Python cannot verify expansion evidence")
    directory, source_root = Path(directory), Path(source_root)
    stages = tuple(stages)
    if not stages or stages != STAGES[:len(stages)]:
        raise ExpansionAuditError("Partial audit must be a nonempty stage prefix")
    plan = verify_plan(directory, source_root)
    plan_hash = sha256(directory / "plan.json")
    if game_class is None:
        if source_root.resolve() != ROOT.resolve():
            raise ExpansionAuditError("A custom source root requires an explicit replay game class")
        from expansion_simulator import ExpansionGame
        game_class = ExpansionGame
    receipts, all_summaries = [], {}
    for stage in stages:
        count = plan["blocks"][stage]
        if stage == "screening":
            jobs = [job(p, n, f, c, count) for p in PROFILES for n in PLAYERS for f in FIELDS for c in POLICIES]
        elif stage == "confirmation":
            jobs = [job(r["profile"], r["players"], f, r[key], count)
                    for r in selection["finalists"] for f in FIELDS for key in ("first", "second")]
        elif stage == "counter_search":
            targets = {(r["profile"], r["players"]): r["first"] for r in selection["finalists"]}
            jobs = [job(p, n, "vs_" + targets[p, n], c, count) for p, n in COUNTER_SETTINGS for c in POLICIES]
        else:
            jobs = [job(r["profile"], r["players"], r["field"], r[key], count)
                    for r in counters["pairs"] for key in ("first", "second")]
        receipt, summaries = audit_stage(directory, plan, stage, jobs, game_class)
        receipts.append(receipt)
        all_summaries[stage] = summaries
        if stage == "screening":
            selection = select_finalists(summaries)
            if read_json(directory / "selection.json") != selection:
                raise ExpansionAuditError("Frozen finalists differ from independent screening ranking")
        elif stage == "counter_search":
            counters = select_counters(summaries, selection)
            if read_json(directory / "counter_selection.json") != counters:
                raise ExpansionAuditError("Frozen counters differ from independent search ranking")
    if stages == STAGES:
        findings = read_json(directory / "findings.json")
        if (findings.get("plan_sha256") != plan_hash or findings.get("source_sha256") != plan["source_sha256"] or
                findings.get("total_games") != sum(r["raw_games"] for r in receipts) or
                findings.get("total_draws") != sum(r["draws"] for r in receipts) or
                findings.get("screening") != all_summaries["screening"] or
                findings.get("confirmation") != all_summaries["confirmation"]):
            raise ExpansionAuditError("Published findings counts differ from independently audited raw outcomes")
    verify_plan(directory, source_root)
    if sha256(directory / "plan.json") != plan_hash:
        raise ExpansionAuditError("Global plan changed during replay")
    return {"schema_version": 1, "status": "passed", "global_plan_sha256": plan_hash,
            "source_sha256": plan["source_sha256"],
            "audit_source_sha256": sha256(source_root / "audit_expansion_research.py"),
            "sample_rule": "first, midpoint and last complete blocks; every physical seat",
            "independence": "raw coordinates, counts, selection and schedules reconstructed without runner helpers; replay shares the expansion engine",
            "stages": receipts, "total_jobs": sum(r["jobs"] for r in receipts),
            "total_raw_games": sum(r["raw_games"] for r in receipts),
            "total_draws": sum(r["draws"] for r in receipts),
            "total_replayed_games": sum(r["replayed_games"] for r in receipts)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--stages", nargs="+", choices=STAGES, default=list(STAGES))
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    receipt = audit(args.results_dir, stages=args.stages)
    rendered = json_bytes(receipt)
    if args.write_receipt:
        if tuple(args.stages) != STAGES:
            raise ExpansionAuditError("Only a full four-stage audit may write the receipt")
        path = args.results_dir / "replay-audit.json"
        if path.exists() or path.is_symlink():
            if path.is_symlink() or not path.is_file() or path.read_bytes() != rendered:
                raise ExpansionAuditError("Existing audit receipt differs; preserve it for review")
        else:
            with path.open("xb") as stream:
                stream.write(rendered)
    print(rendered.decode("utf-8"), end="")


if __name__ == "__main__":
    main()
