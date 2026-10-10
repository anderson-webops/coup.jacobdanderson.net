"""Validate frozen panels and calculate paired finalist comparisons."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from math import sqrt
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).parent


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(folder: Path) -> dict:
    manifest = json.loads((folder / "study_manifest.json").read_text())
    for name, expected in manifest["checksums_sha256"].items():
        actual_path = ROOT / name if name.endswith(".py") else folder / name
        if digest(actual_path) != expected:
            raise ValueError(f"Study input or output changed since run: {actual_path}")
    return manifest


def main() -> None:
    plan = json.loads((ROOT / "confirmation_plan.json").read_text())
    screen = verify_manifest(ROOT)
    confirm = verify_manifest(ROOT / "confirmation")
    if digest(ROOT / "results.csv") != plan["screening_results_sha256"]:
        raise ValueError("screening results do not match the frozen confirmation plan")
    if confirm["panel"] != plan["confirmation_panel"] or confirm["games_per_seat"] != plan["confirmation_games_per_seat"]:
        raise ValueError("confirmation panel does not match the frozen plan")
    if confirm["candidates"] != plan["confirmation_candidates"]:
        raise ValueError("confirmation candidate roster changed")
    if confirm["fields"] != plan["confirmation_fields"]:
        raise ValueError("confirmation field roster changed")
    screen_rows = read_rows(ROOT / "results.csv")
    confirm_rows = read_rows(ROOT / "confirmation" / "results.csv")
    raw_rows = read_rows(ROOT / "confirmation" / "games.csv")
    if sum(int(row["games"]) for row in screen_rows) != plan["screening_games"]:
        raise ValueError("screening game count changed")
    if len(raw_rows) != sum(int(row["games"]) for row in confirm_rows):
        raise ValueError("raw and summarized confirmation counts differ")

    outcomes = defaultdict(dict)
    raw_counts = defaultdict(lambda: [0, 0, 0])
    for row in raw_rows:
        key = (int(row["seat"]), int(row["game"]))
        group = (row["field"], row["policy"])
        if key in outcomes[group]:
            raise ValueError("duplicate confirmation game identity")
        outcomes[group][key] = int(row["won"])
        counts = raw_counts[group]
        counts[0] += int(row["won"])
        counts[1] += int(row["draw"])
        counts[2] += 1
    for row in confirm_rows:
        expected = (int(row["wins"]), int(row["draws"]), int(row["games"]))
        actual = tuple(raw_counts[row["field"], row["policy"]])
        if actual != expected:
            raise ValueError(f"confirmation summary differs from raw games: {row['field']} {row['policy']}")
    findings = []
    simultaneous_z = NormalDist().inv_cdf(1 - 0.05 / (2 * len(confirm["fields"])))
    for field in confirm["fields"]:
        ranking = sorted(
            (row for row in confirm_rows if row["players"] == "4" and row["field"] == field),
            key=lambda row: (-float(row["win_rate"]), row["policy"]),
        )
        first, second = ranking[:2]
        planned_pair = set(plan["shortlist_by_field"][field][:2])
        if {first["policy"], second["policy"]} != planned_pair:
            raise ValueError(f"confirmation top-two pair was not prespecified by screening: {field}")
        first_out = outcomes[field, first["policy"]]
        second_out = outcomes[field, second["policy"]]
        if first_out.keys() != second_out.keys():
            raise ValueError("paired candidates have different seed and seat panels")
        differences = [first_out[key] - second_out[key] for key in sorted(first_out)]
        count = len(differences)
        mean = sum(differences) / count
        variance = sum((value - mean) ** 2 for value in differences) / (count - 1)
        half = simultaneous_z * sqrt(variance / count)
        findings.append({
            "field": field,
            "field_label": {"honest": "Honest", "bluffing": "Bluffing", "skeptical": "Skeptical", "mixed": "Mixed"}[field],
            "leader": first["policy"],
            "wins": int(first["wins"]),
            "games": int(first["games"]),
            "draws": int(first["draws"]),
            "win_rate": float(first["win_rate"]),
            "runner_up": second["policy"],
            "runner_rate": float(second["win_rate"]),
            "difference": round(mean, 6),
            "lower95": round(mean - half, 6),
            "upper95": round(mean + half, 6),
            "paired_games": count,
            "preselected_screening_pair": plan["shortlist_by_field"][field][:2],
            "separated_at_family95": mean - half > 0,
        })
    result = {
        "screening_games": sum(int(row["games"]) for row in screen_rows),
        "screening_draws": sum(int(row["draws"]) for row in screen_rows),
        "confirmation_games": len(raw_rows),
        "confirmation_draws": sum(int(row["draws"]) for row in confirm_rows),
        "findings": findings,
        "comparison_method": "paired mean of winner indicators across identical seat and seed indices; simultaneous normal 95% intervals across four preselected field comparisons using Bonferroni correction",
    }
    (ROOT / "findings.json").write_text(json.dumps(result, indent=2) + "\n")
    for item in findings:
        print(item["field"], item["leader"], item["win_rate"], item["difference"], item["lower95"], item["upper95"], item["separated_at_family95"])


if __name__ == "__main__":
    main()
