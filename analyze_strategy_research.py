"""Independently reconcile staged Coup outcomes before reporting new findings.

The frozen 2026-10-10 site study is deliberately outside this module. Stage
plans, manifests, compressed raw games, and summaries live in a separate
research_results directory. No game engine is imported here.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from research_statistics import StudyDataError, audit_panel, paired_compare


PROJECT = Path(__file__).resolve().parent
DEFAULT_STUDY = PROJECT / "research_results" / "2026-10-12"
STAGES = ("tuning", "screening", "confirmation", "counter_search",
          "counters", "ablations", "stress")
RAW_COLUMNS = ("stage", "players", "field", "candidate", "block", "rotation",
               "seed", "winner", "focal_seat", "won", "draw", "turns")
SUMMARY_COLUMNS = ("stage", "players", "field", "candidate", "games", "wins",
                   "draws", "win_rate", "mean_turns", "blocks")
SAFE_NAME = re.compile(r"^[A-Za-z0-9_]+$")
BASE_FIELDS = ("honest", "bluffing", "skeptical", "rational", "learning", "random", "mixed")
STRESS_FIELDS = ("selfplay", "assault", "economy", "chaos", "alternating", "mixed")


class ResearchAuditError(ValueError):
    """A stage is incomplete or differs from its frozen plan and manifest."""


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _json(path: Path) -> dict:
    try:
        result = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise ResearchAuditError(f"cannot read JSON: {path}") from exc
    if not isinstance(result, dict):
        raise ResearchAuditError(f"JSON object required: {path}")
    return result


def _int(value: object, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ResearchAuditError(f"invalid {name}: {value!r}") from exc
    if isinstance(value, bool) or str(result) != str(value) or result < 0:
        raise ResearchAuditError(f"invalid {name}: {value!r}")
    return result


def _job_key(row: dict) -> tuple[int, str, str]:
    return (_int(row.get("players"), "players"), row.get("field"), row.get("candidate"))


def _job_file(job: dict) -> str:
    players, field, candidate = _job_key(job)
    if not 2 <= players <= 6 or not isinstance(field, str) or not SAFE_NAME.fullmatch(field) or not isinstance(candidate, str) or not SAFE_NAME.fullmatch(candidate):
        raise ResearchAuditError(f"unsafe or invalid job identity: {job}")
    return f"{players}-{field}-{candidate}.csv.gz"


def _diagnostic_file(job: dict) -> str:
    return _job_file(job)[:-3] + ".diagnostics.json"


def _rate(value: object, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ResearchAuditError(f"invalid {name}: {value!r}") from exc
    if not math.isfinite(result):
        raise ResearchAuditError(f"invalid {name}: {value!r}")
    return result


def _counts(mapping: object, name: str) -> Counter:
    if not isinstance(mapping, dict):
        raise ResearchAuditError(f"{name} must be a mapping")
    if any(not isinstance(key, str) or not key for key in mapping):
        raise ResearchAuditError(f"{name} has invalid keys")
    return Counter({key: _int(value, f"{name}.{key}") for key, value in mapping.items()})


def _expected_seed(stage: str, players: int, field_index: int, block: int) -> int:
    return 202610120000000 + STAGES.index(stage) * 10**12 + players * 10**9 + field_index * 10**6 + block


def _source_hashes(plan: dict) -> dict[str, str]:
    mapping = plan.get("source_sha256")
    if not isinstance(mapping, dict) or not mapping:
        raise ResearchAuditError("global plan needs source_sha256 mapping")
    for name, expected in mapping.items():
        if not isinstance(name, str) or Path(name).is_absolute() or ".." in Path(name).parts or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ResearchAuditError("invalid source_sha256 entry")
        source = PROJECT / name
        if not source.is_file() or digest(source) != expected:
            raise ResearchAuditError(f"source changed since plan freeze: {name}")
    return mapping


def _stage_files(stage_dir: Path, jobs: list[dict]) -> set[str]:
    expected = {_job_file(job) for job in jobs}
    if len(expected) != len(jobs):
        raise ResearchAuditError(f"duplicate planned job in {stage_dir.name}")
    actual = {path.name for path in stage_dir.glob("*.csv.gz")}
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ResearchAuditError(f"raw job inventory differs in {stage_dir.name}: missing={missing[:4]} extra={extra[:4]}")
    return expected


def _raw_rows(path: Path):
    try:
        with gzip.open(path, "rt", newline="") as file:
            reader = csv.DictReader(file)
            if tuple(reader.fieldnames or ()) != RAW_COLUMNS:
                raise ResearchAuditError(f"raw schema differs: {path}")
            for row in reader:
                if set(row) != set(RAW_COLUMNS) or any(value is None for value in row.values()):
                    raise ResearchAuditError(f"malformed raw row: {path}")
                yield row
    except (OSError, EOFError) as exc:
        raise ResearchAuditError(f"damaged compressed raw outcomes: {path}") from exc


def _summaries(path: Path) -> dict[tuple[int, str, str], dict]:
    try:
        with path.open(newline="") as file:
            reader = csv.DictReader(file)
            if tuple(reader.fieldnames or ()) != SUMMARY_COLUMNS:
                raise ResearchAuditError(f"summary schema differs: {path}")
            rows = list(reader)
    except OSError as exc:
        raise ResearchAuditError(f"missing summaries: {path}") from exc
    result = {}
    for row in rows:
        key = _job_key(row)
        if key in result:
            raise ResearchAuditError(f"duplicate summary identity: {key}")
        result[key] = row
    return result


def _verify_manifest(study_dir: Path, stage_dir: Path, global_plan: dict, plan: dict,
                     expected_files: set[str]) -> dict:
    manifest = _json(stage_dir / "manifest.json")
    if manifest.get("stage") != stage_dir.name:
        raise ResearchAuditError(f"manifest stage differs: {stage_dir.name}")
    if manifest.get("plan_sha256") != digest(stage_dir / "plan.json"):
        raise ResearchAuditError(f"stage plan hash differs: {stage_dir.name}")
    if manifest.get("global_plan_sha256") != digest(study_dir / "plan.json"):
        raise ResearchAuditError(f"global plan hash differs: {stage_dir.name}")
    if manifest.get("source_sha256") != global_plan.get("source_sha256"):
        raise ResearchAuditError(f"source fingerprints differ: {stage_dir.name}")
    files = manifest.get("files")
    expected_inventory = ({"plan.json", "summaries.csv", "diagnostics.json"} |
                          expected_files |
                          {_diagnostic_file(job) for job in plan["jobs"]})
    actual_inventory = {path.name for path in stage_dir.iterdir() if path.is_file() and path.name != "manifest.json"}
    if (not isinstance(files, dict) or set(files) != expected_inventory or
            actual_inventory != expected_inventory or
            any(path.is_dir() for path in stage_dir.iterdir())):
        raise ResearchAuditError(f"manifest file inventory differs: {stage_dir.name}")
    for name, expected in files.items():
        if (not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected)
                or digest(stage_dir / name) != expected):
            raise ResearchAuditError(f"output hash differs: {stage_dir.name}/{name}")
    return manifest


def _verify_job_diagnostic(path: Path, stage: str, job: dict, summary: dict,
                           seats: dict, actions: Counter, events: Counter) -> None:
    record = _json(path)
    if record.get("stage") != stage or record.get("job") != job:
        raise ResearchAuditError(f"job diagnostic identity differs: {path}")
    raw_path = path.with_name(path.name.replace(".csv.diagnostics.json", ".csv.gz"))
    if record.get("raw_sha256") != digest(raw_path):
        raise ResearchAuditError(f"job diagnostic raw hash differs: {path}")
    reported = record.get("summary")
    if not isinstance(reported, dict) or set(reported) != set(SUMMARY_COLUMNS):
        raise ResearchAuditError(f"job diagnostic summary schema differs: {path}")
    for name in ("stage", "field", "candidate"):
        if reported[name] != summary[name]:
            raise ResearchAuditError(f"job diagnostic summary {name} differs: {path}")
    for name in ("players", "games", "wins", "draws", "blocks"):
        if _int(reported[name], name) != summary[name]:
            raise ResearchAuditError(f"job diagnostic summary {name} differs: {path}")
    for name in ("win_rate", "mean_turns"):
        if abs(_rate(reported[name], name) - summary[name]) > 1e-12:
            raise ResearchAuditError(f"job diagnostic summary {name} differs: {path}")
    if record.get("seats") != seats:
        raise ResearchAuditError(f"job diagnostic seats differ from raw: {path}")
    actions.update(_counts(record.get("actions"), "actions"))
    events.update(_counts(record.get("events"), "events"))


def _verify_stage_diagnostics(stage_dir: Path, games: int, draws: int,
                              seats: dict, actions: Counter, events: Counter) -> None:
    record = _json(stage_dir / "diagnostics.json")
    if (_int(record.get("games"), "games") != games or
            _int(record.get("draws"), "draws") != draws or
            record.get("seats") != seats or
            _counts(record.get("actions"), "actions") != actions or
            _counts(record.get("events"), "events") != events):
        raise ResearchAuditError(f"stage diagnostics differ from jobs: {stage_dir.name}")


def audit_stage(study_dir: Path, stage: str, *, global_plan: dict | None = None) -> dict:
    """Verify one complete stage without loading more than one field/count cell."""
    study_dir = Path(study_dir)
    if stage not in STAGES:
        raise ValueError(f"unknown stage: {stage}")
    global_plan = global_plan or _json(study_dir / "plan.json")
    _source_hashes(global_plan)
    stage_dir = study_dir / stage
    plan = _json(stage_dir / "plan.json")
    if plan.get("stage") != stage or not isinstance(plan.get("jobs"), list) or not plan["jobs"]:
        raise ResearchAuditError(f"invalid stage plan: {stage}")
    if (plan.get("global_plan_sha256") != digest(study_dir / "plan.json") or
            plan.get("source_sha256") != global_plan.get("source_sha256")):
        raise ResearchAuditError(f"stage plan provenance differs: {stage}")
    jobs = plan["jobs"]
    planned_fields = list(dict.fromkeys(job.get("field") for job in jobs))
    if plan.get("fields") != planned_fields:
        raise ResearchAuditError(f"stage field order differs from jobs: {stage}")
    files = _stage_files(stage_dir, jobs)
    manifest = _verify_manifest(study_dir, stage_dir, global_plan, plan, files)
    summaries = _summaries(stage_dir / "summaries.csv")
    job_map = {_job_key(job): job for job in jobs}
    if set(summaries) != set(job_map):
        raise ResearchAuditError(f"summary job inventory differs: {stage}")
    by_cell = defaultdict(list)
    for job in jobs:
        players, field, candidate = _job_key(job)
        blocks = _int(job.get("blocks"), "blocks")
        if blocks < 1:
            raise ResearchAuditError("each job needs at least one rotation block")
        by_cell[players, field].append(job)
    total_games = total_wins = total_draws = 0
    all_actions, all_events, all_seats = Counter(), Counter(), {}
    audited_rows = {}
    for (players, field), cell_jobs in sorted(by_cell.items()):
        block_counts = {_int(job["blocks"], "blocks") for job in cell_jobs}
        if len(block_counts) != 1:
            raise ResearchAuditError(f"unequal block counts within {stage} {players} {field}")
        blocks = block_counts.pop()
        cell_rows = []
        for job in cell_jobs:
            candidate = job["candidate"]
            key = players, field, candidate
            path = stage_dir / _job_file(job)
            turns = wins = draws = games = 0
            seats = {str(i): {"wins": 0, "draws": 0, "games": 0} for i in range(players)}
            for row in _raw_rows(path):
                if row.get("stage") != stage or _job_key(row) != key:
                    raise ResearchAuditError(f"raw game belongs to another job: {path}")
                block = _int(row["block"], "block")
                rotation = _int(row["rotation"], "rotation")
                seed = _int(row["seed"], "seed")
                if (block >= blocks or rotation >= players or
                        _int(row["focal_seat"], "focal_seat") != rotation or
                        seed != _expected_seed(stage, players, planned_fields.index(field), block)):
                    raise ResearchAuditError(f"raw seed or rotation differs from plan: {path}")
                won, draw = _int(row["won"], "won"), _int(row["draw"], "draw")
                wins += won
                draws += draw
                turns += _int(row["turns"], "turns")
                games += 1
                seats[str(rotation)]["wins"] += won
                seats[str(rotation)]["draws"] += draw
                seats[str(rotation)]["games"] += 1
                cell_rows.append(row)
            if games != players * blocks:
                raise ResearchAuditError(f"raw game count differs from plan: {path}")
            summary = summaries[key]
            if summary["stage"] != stage or (games, wins, draws, blocks) != tuple(
                _int(summary[name], name) for name in ("games", "wins", "draws", "blocks")
            ):
                raise ResearchAuditError(f"summary counts differ from raw: {path}")
            if abs(_rate(summary["win_rate"], "win_rate") - wins / games) > 1e-12 or abs(_rate(summary["mean_turns"], "mean_turns") - turns / games) > 1e-12:
                raise ResearchAuditError(f"summary rates differ from raw: {path}")
            row_summary = {
                "stage": stage, "players": players, "field": field,
                "candidate": candidate, "blocks": blocks, "games": games,
                "wins": wins, "draws": draws, "win_rate": wins / games,
                "mean_turns": turns / games,
            }
            audited_rows[key] = row_summary
            diagnostic_name = _diagnostic_file(job)
            _verify_job_diagnostic(stage_dir / diagnostic_name, stage, job,
                                   row_summary, seats, all_actions, all_events)
            all_seats[_job_file(job)] = seats
            total_games += games
            total_wins += wins
            total_draws += draws
        try:
            audit_panel(cell_rows, players, field,
                        [job["candidate"] for job in cell_jobs], blocks, stage=stage)
        except StudyDataError as exc:
            raise ResearchAuditError(f"raw panel invalid in {stage} {players} {field}: {exc}") from exc
    if _int(manifest.get("scheduled_games"), "scheduled_games") != total_games:
        raise ResearchAuditError(f"manifest scheduled game count differs: {stage}")
    _verify_stage_diagnostics(stage_dir, total_games, total_draws,
                              all_seats, all_actions, all_events)
    return {
        "stage": stage, "plan": plan, "manifest": manifest,
        "plan_sha256": digest(stage_dir / "plan.json"),
        "games": total_games, "wins": total_wins, "draws": total_draws,
        "jobs": len(jobs), "rows": audited_rows,
    }


def _pair_record(stage_dir: Path, stage: str, pair: dict, family_size: int) -> dict:
    players = _int(pair.get("players"), "players")
    field = pair.get("field")
    first = pair.get("first", pair.get("counter"))
    second = pair.get("second", pair.get("target"))
    if not isinstance(field, str) or not first or not second:
        raise ResearchAuditError(f"invalid frozen pair in {stage}")
    first_path = stage_dir / f"{players}-{field}-{first}.csv.gz"
    second_path = stage_dir / f"{players}-{field}-{second}.csv.gz"
    if not first_path.is_file() or not second_path.is_file():
        raise ResearchAuditError(f"frozen pair missing candidate file in {stage}")
    rows = list(_raw_rows(first_path)) + list(_raw_rows(second_path))
    blocks = _int(pair.get("blocks", len(rows) // (2 * players)), "blocks")
    try:
        result = paired_compare(rows, players, field, first, second,
                                family_size=family_size, stage=stage,
                                expected_blocks=blocks)
    except StudyDataError as exc:
        raise ResearchAuditError(f"frozen pair invalid in {stage}: {exc}") from exc
    if stage == "counters":
        result["self_play_reference"] = 1 / players
        result["counter_exceeds_target_control"] = result["conservative_supports_positive"]
    return result


def _frozen_pairs(study_dir: Path, stage_result: dict, expected_family: int) -> list[dict]:
    plan = stage_result["plan"]
    pairs = plan.get("pairs")
    if not isinstance(pairs, list) or len(pairs) != expected_family:
        raise ResearchAuditError(f"{stage_result['stage']} needs {expected_family} frozen pairs")
    keys = set()
    results = []
    for pair in pairs:
        if not isinstance(pair, dict):
            raise ResearchAuditError("pair must be an object")
        key = (_int(pair.get("players"), "players"), pair.get("field"),
               pair.get("first", pair.get("counter")),
               pair.get("second", pair.get("target")))
        if key in keys:
            raise ResearchAuditError(f"duplicate frozen pair: {key}")
        keys.add(key)
        results.append(_pair_record(study_dir / stage_result["stage"],
                                    stage_result["stage"], pair, expected_family))
    return results


def _rank_global(rows: list[dict]) -> list[str]:
    names = sorted({row["candidate"] for row in rows})
    return sorted(names, key=lambda name: (
        -sum(row["players"] * row["win_rate"] for row in rows if row["candidate"] == name)
        / sum(row["candidate"] == name for row in rows), name))


def _selected_pairs(rows: list[dict]) -> list[dict]:
    cells = sorted({(row["players"], row["field"]) for row in rows})
    result = []
    for players, field in cells:
        ranked = sorted((row for row in rows if row["players"] == players and row["field"] == field),
                        key=lambda row: (-row["win_rate"], row["candidate"]))
        result.append({"players": players, "field": field,
                       "first": ranked[0]["candidate"], "second": ranked[1]["candidate"]})
    return result


def _verify_selection(study_dir: Path, stages: dict, global_plan: dict) -> None:
    tuning_rows = list(stages["tuning"]["rows"].values())
    selected_tuners = _rank_global(tuning_rows)[:6]
    screening = stages["screening"]
    if screening["plan"].get("extra", {}).get("tuners_selected") != selected_tuners:
        raise ResearchAuditError("screening tuners differ from audited tuning results")
    screening_names = {row["candidate"] for row in screening["rows"].values()}
    expected_screening = set(selected_tuners) | set(global_plan["controls"]) | {
        "card_cautious", "card_balanced", "card_bold", "public_learning",
        "eliminator", "defensive", "exchange_builder"}
    if screening_names != expected_screening:
        raise ResearchAuditError("screening candidates differ from frozen selection")
    screening_rows = list(screening["rows"].values())
    confirmation_pairs = _selected_pairs(screening_rows)
    ranking = _rank_global(screening_rows)
    targets = [ranking[0], next(name for name in ranking if name in {
        "card_cautious", "card_balanced", "card_bold", "public_learning",
        "eliminator", "defensive", "exchange_builder"} and name != ranking[0])]
    finalists = sorted({pair[name] for pair in confirmation_pairs for name in ("first", "second")}
                       | {"baseline", "card_balanced", "public_learning"})
    selection = _json(study_dir / "selection.json")
    if selection != {"confirmation_pairs": confirmation_pairs, "finalists": finalists,
                     "counter_targets": targets, "screening_global_rank": ranking}:
        raise ResearchAuditError("selection record differs from audited screening")
    if stages["confirmation"]["plan"].get("pairs") != confirmation_pairs:
        raise ResearchAuditError("confirmation pairs differ from screened selection")
    if {row["candidate"] for row in stages["confirmation"]["rows"].values()} != set(finalists):
        raise ResearchAuditError("confirmation candidate union differs from frozen selection")
    if (stages["counter_search"]["plan"].get("extra", {}).get("targets") != targets or
            {row["field"] for row in stages["counter_search"]["rows"].values()} !=
            {"vs_" + target for target in targets}):
        raise ResearchAuditError("counter search targets differ from screening")
    search_rows = list(stages["counter_search"]["rows"].values())
    counter_pairs = []
    for players in (2, 4):
        for target in targets:
            field = "vs_" + target
            contenders = sorted((row for row in search_rows
                                 if row["players"] == players and row["field"] == field and row["candidate"] != target),
                                key=lambda row: (-row["win_rate"], row["candidate"]))
            if not contenders:
                raise ResearchAuditError("counter search lacks contenders")
            counter_pairs.append({"players": players, "field": field,
                                  "first": contenders[0]["candidate"], "second": target})
    if (_json(study_dir / "counter_selection.json") != {"pairs": counter_pairs} or
            stages["counters"]["plan"].get("pairs") != counter_pairs):
        raise ResearchAuditError("confirmed counters differ from search selection")

    ablation_names = tuple(global_plan["schedule"]["ablations"]["components"])
    ablation_pairs = [{"players": players, "field": field,
                       "first": "public_learning", "second": name}
                      for players in (2, 4) for field in BASE_FIELDS for name in ablation_names]
    if stages["ablations"]["plan"].get("pairs") != ablation_pairs:
        raise ResearchAuditError("ablation family differs from frozen global plan")
    expected = {
        "tuning": {(n, field, f"search_{i:02d}", 32)
                   for n in (2, 4, 6) for field in BASE_FIELDS for i in range(24)},
        "screening": {(n, field, name, 100)
                      for n in range(2, 7) for field in BASE_FIELDS for name in screening_names},
        "confirmation": {(n, field, name, 1000)
                         for n in range(2, 7) for field in BASE_FIELDS for name in finalists},
        "counter_search": {(n, "vs_" + target, name, 32)
                           for n in (2, 4) for target in targets for name in screening_names},
        "counters": {(pair["players"], pair["field"], name, 1000)
                     for pair in counter_pairs for name in (pair["first"], pair["second"])},
        "ablations": {(n, field, name, 500)
                      for n in (2, 4) for field in BASE_FIELDS
                      for name in ("public_learning",) + ablation_names},
        "stress": {(6, field, name, 100)
                   for field in STRESS_FIELDS
                   for name in ("card_cautious", "card_balanced", "card_bold",
                                "public_learning", "eliminator", "defensive",
                                "exchange_builder", "baseline", "bluff_heavy",
                                "challenge_heavy")},
    }
    for stage, cells in expected.items():
        actual = {(row["players"], row["field"], row["candidate"], row["blocks"])
                  for row in stages[stage]["rows"].values()}
        if actual != cells:
            raise ResearchAuditError(f"{stage} job schedule differs from frozen design")


def _confirmation_descriptives(stage_result: dict) -> tuple[list[dict], list[dict], list[dict]]:
    by_cell = defaultdict(list)
    by_candidate = defaultdict(dict)
    for row in stage_result["rows"].values():
        key = row["players"], row["field"]
        by_cell[key].append(row)
        by_candidate[row["players"], row["candidate"]][row["field"]] = row
    observed = []
    for (players, field), entries in sorted(by_cell.items()):
        ordered = sorted(entries, key=lambda row: (-row["win_rate"], row["candidate"]))
        observed.append({"players": players, "field": field,
                         "observed_leader": ordered[0]["candidate"],
                         "observed_rate": ordered[0]["win_rate"],
                         "runner_up": ordered[1]["candidate"] if len(ordered) > 1 else None,
                         "runner_up_rate": ordered[1]["win_rate"] if len(ordered) > 1 else None})
    fields = sorted({row["field"] for row in stage_result["rows"].values()})
    broad = []
    sensitivity = []
    alternative_weights = {field: (2 if field in ("rational", "learning") else 1)
                           for field in fields}
    for (players, candidate), entries in sorted(by_candidate.items()):
        if set(entries) != set(fields):
            raise ResearchAuditError("confirmation union candidate absent from a field")
        worst = min(entries.values(), key=lambda row: (row["win_rate"], row["field"]))
        broad.append({"players": players, "candidate": candidate,
                      "equal_field_mean": sum(row["win_rate"] for row in entries.values()) / len(fields),
                      "worst_field": worst["field"], "worst_rate": worst["win_rate"]})
        sensitivity.append({"players": players, "candidate": candidate,
                            "scenario": "double_rational_learning",
                            "scenario_mean": sum(entries[field]["win_rate"] * alternative_weights[field]
                                                 for field in fields) / sum(alternative_weights.values()),
                            "equal_field_mean": broad[-1]["equal_field_mean"]})
    return observed, broad, sensitivity


def _pooled_summaries(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)
    answer = []
    for identity, entries in sorted(grouped.items()):
        games = sum(row["games"] for row in entries)
        wins = sum(row["wins"] for row in entries)
        draws = sum(row["draws"] for row in entries)
        answer.append(dict(zip(keys, identity)) | {
            "games": games, "wins": wins, "draws": draws,
            "win_rate": wins / games,
            "mean_turns": sum(row["mean_turns"] * row["games"] for row in entries) / games,
            "cells": len(entries),
        })
    return answer


def _verify_saved_findings(study_dir: Path, result: dict) -> None:
    saved = _json(study_dir / "findings.json")
    if saved != result:
        raise ResearchAuditError("saved findings.json differs from audited raw outcomes")
    try:
        markdown = (study_dir / "FINDINGS.md").read_text()
    except OSError as exc:
        raise ResearchAuditError("saved FINDINGS.md is missing") from exc
    if markdown != _markdown(result):
        raise ResearchAuditError("saved FINDINGS.md differs from audited findings")


def analyze_study(study_dir: Path = DEFAULT_STUDY, *, write: bool = True,
                  verify_saved: bool = False) -> dict:
    """Verify all seven stages, then analyze only prespecified contrasts."""
    if write and verify_saved:
        raise ValueError("choose writing or saved-findings verification")
    study_dir = Path(study_dir)
    global_plan = _json(study_dir / "plan.json")
    _source_hashes(global_plan)
    stages = {stage: audit_stage(study_dir, stage, global_plan=global_plan) for stage in STAGES}
    _verify_selection(study_dir, stages, global_plan)
    comparisons = {}
    for stage, family in (("confirmation", 35), ("counters", 4), ("ablations", 56)):
        comparisons[stage] = _frozen_pairs(study_dir, stages[stage], family)
    observed, broad, sensitivity = _confirmation_descriptives(stages["confirmation"])
    confirmation_rows = sorted(stages["confirmation"]["rows"].values(),
                               key=lambda row: (row["players"], row["field"], row["candidate"]))
    observed_map = {(row["players"], row["field"]): row for row in observed}
    confirmation_pairs = []
    for pair in comparisons["confirmation"]:
        leader = observed_map[(pair["players"], pair["field"])]
        confirmation_pairs.append(pair | {
            "observed_leader": leader["observed_leader"],
            "observed_leader_rate": leader["observed_rate"],
            "observed_leader_is_preselected": leader["observed_leader"] in
            (pair["first"], pair["second"]),
        })
    limitations = [
        "Only the finite frozen policy population and seven programmed opponent fields were tested.",
        "Observed leaders, pooled rates, and worst-field rankings are descriptive post-confirmation comparisons; the simultaneous paired intervals cover the 35 preselected pairs only.",
        "The normal family intervals are approximate. The Hoeffding family intervals are conservative under independent rotation blocks and may leave small differences unresolved.",
        "All games use the programmed standard base-game rules, response order, public-information model, and 1000-turn cap; human opponents may behave differently.",
        "Two-player starting coins are asymmetric; compare two-player results separately from larger tables.",
        "Counter and ablation checks have their own frozen families and do not prove a policy is universally optimal.",
    ]
    stage_summaries = {stage: {name: report[name] for name in
                              ("games", "wins", "draws", "jobs", "plan_sha256")}
                       for stage, report in stages.items()}
    result = {
        "scope": "finite tested Coup policies and frozen opponent fields",
        "global_plan_sha256": digest(study_dir / "plan.json"),
        "source_sha256": global_plan["source_sha256"],
        "total_games": sum(item["games"] for item in stage_summaries.values()),
        "stages": stage_summaries,
        "confirmation_rows": confirmation_rows,
        "confirmation_pairs": confirmation_pairs,
        "counters": comparisons["counters"],
        "ablations": comparisons["ablations"],
        "observed_leaders": observed,
        "equal_field_robustness": broad,
        "field_weighting_sensitivity": sensitivity,
        "overall": _pooled_summaries(confirmation_rows, ("candidate",)),
        "by_player": _pooled_summaries(confirmation_rows, ("players", "candidate")),
        "limitations": limitations,
    }
    if write:
        (study_dir / "findings.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        (study_dir / "FINDINGS.md").write_text(_markdown(result))
    if verify_saved:
        _verify_saved_findings(study_dir, result)
    return result


def _markdown(result: dict) -> str:
    lines = ["# Coup strategy research findings", "",
             "These results compare a finite, frozen policy population under the stated Coup rules and opponent fields. They do not establish an unrestricted optimal strategy or predict human play.", "",
             "## Verified study size", "",
             "| Stage | Games | Draws | Jobs |", "| --- | ---: | ---: | ---: |"]
    for stage in STAGES:
        totals = result["stages"][stage]
        lines.append(f"| {stage} | {totals['games']:,} | {totals['draws']:,} | {totals['jobs']:,} |")
    lines += ["", "## Frozen confirmation pairs", "",
              "The first and second candidates in each row were selected before confirmation. A positive difference favors the first. The normal family interval is approximate; the Hoeffding family interval is conservative.", "",
              "| Players | Field | Preselected first | Preselected second | Difference | Normal family 95% | Conservative family 95% |",
              "| ---: | --- | --- | --- | ---: | --- | --- |"]
    for row in result["confirmation_pairs"]:
        lines.append(f"| {row['players']} | {row['field']} | {row['first']} | {row['second']} | {row['difference']:+.1%} | [{row['normal_family_lower']:+.1%}, {row['normal_family_upper']:+.1%}] | [{row['conservative_family_lower']:+.1%}, {row['conservative_family_upper']:+.1%}] |")
    lines += ["", "## Observed leaders", "",
              "These are point-estimate rankings across the frozen union. The pairwise intervals above do not establish a winner over every union member.", "",
              "| Players | Field | Highest observed | Win rate |",
              "| ---: | --- | --- | ---: |"]
    for row in result["observed_leaders"]:
        lines.append(f"| {row['players']} | {row['field']} | {row['observed_leader']} | {row['observed_rate']:.1%} |")
    lines += ["", "## Counter and ablation checks", "",
              "Counter targets and ablation components were frozen in their stage plans. Their intervals form separate comparison families. The complete values are in findings.json.", "",
              "## Limits", "",
              *[f"- {limitation}" for limitation in result["limitations"]], ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--stage", choices=STAGES, help="audit one stage without writing findings")
    parser.add_argument("--verify-only", action="store_true", help="audit all stages and require saved findings to match")
    args = parser.parse_args()
    if args.stage:
        report = audit_stage(args.study_dir, args.stage)
        print(f"Verified {args.stage}: {report['games']} games, {report['draws']} draws")
    else:
        result = analyze_study(args.study_dir, write=not args.verify_only,
                               verify_saved=args.verify_only)
        print(f"Verified {result['total_games']} games across {len(STAGES)} stages")


if __name__ == "__main__":
    main()
