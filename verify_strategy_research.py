"""Audit frozen outcomes without requiring identical platform float rounding.

The preregistered analyzer and all study bytes remain unchanged. CPython 3.12
changed float summation; libm and NormalDist also have platform rounding. Only
specified derived float leaves may differ by 1e-14 absolute, with no relative
tolerance. Counts, direct rates, selections, flags, structure and hashes remain
exact. The frozen canonical findings render byte for byte. Publication byte hashes
are checked separately by check_site.py.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from analyze_strategy_research import DEFAULT_STUDY, ResearchAuditError, _markdown, analyze_study

MAX_ABSOLUTE_ROUNDING = 1e-14
COMPARISON_FLOATS = frozenset({
    "difference", "normal_family_lower", "normal_family_upper",
    "conservative_family_lower", "conservative_family_upper",
})
DERIVED_FLOATS = {
    "confirmation_pairs": COMPARISON_FLOATS,
    "counters": COMPARISON_FLOATS,
    "ablations": COMPARISON_FLOATS,
    "equal_field_robustness": frozenset({"equal_field_mean"}),
    "field_weighting_sensitivity": frozenset({"equal_field_mean", "scenario_mean"}),
}


def _unique_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ResearchAuditError(f"duplicate saved findings key: {key}")
        value[key] = item
    return value


def compare_findings(saved: object, computed: object) -> list[dict]:
    """Require exact evidence except narrowly allowed derived float rounding."""
    differences = []

    def walk(first, second, path):
        label = "/".join(map(str, path)) or "<root>"
        if type(first) is not type(second):
            raise ResearchAuditError(f"saved findings type differs at {label}")
        if isinstance(first, dict):
            if first.keys() != second.keys():
                raise ResearchAuditError(f"saved findings keys differ at {label}")
            for key in sorted(first):
                walk(first[key], second[key], path + (key,))
        elif isinstance(first, list):
            if len(first) != len(second):
                raise ResearchAuditError(f"saved findings length differs at {label}")
            for index, (a, b) in enumerate(zip(first, second)):
                walk(a, b, path + (index,))
        elif isinstance(first, float):
            if not math.isfinite(first) or not math.isfinite(second):
                raise ResearchAuditError(f"nonfinite saved findings at {label}")
            if math.copysign(1.0, first) != math.copysign(1.0, second):
                raise ResearchAuditError(f"saved findings sign differs at {label}")
            if first == second:
                return
            allowed = (len(path) == 3 and type(path[1]) is int and
                       path[2] in DERIVED_FLOATS.get(path[0], ()))
            difference = abs(first - second)
            same_sign = (first != 0.0 and second != 0.0 and (first > 0) == (second > 0))
            if not allowed or not same_sign or difference > MAX_ABSOLUTE_ROUNDING:
                raise ResearchAuditError(f"saved findings number differs at {label}: {difference:.17g}")
            differences.append({"path": label, "absolute_difference": difference})
        elif first != second:
            raise ResearchAuditError(f"saved findings value differs at {label}")

    walk(saved, computed, ())
    return differences


def verify_saved(study_dir: Path, computed: dict) -> tuple[dict, dict]:
    study_dir = Path(study_dir)
    raw = (study_dir / "findings.json").read_bytes()
    saved = json.loads(raw, object_pairs_hook=_unique_keys)
    if raw != (json.dumps(saved, indent=2, sort_keys=True) + "\n").encode("utf-8"):
        raise ResearchAuditError("saved findings.json is not its frozen canonical representation")
    differences = compare_findings(saved, computed)
    for section, value in (("equal_field_robustness", "equal_field_mean"),
                           ("field_weighting_sensitivity", "scenario_mean")):
        def ranking(result):
            return [(row["players"], row["candidate"]) for row in
                    sorted(result[section], key=lambda row: (row["players"], -row[value], row["candidate"]))]
        if ranking(saved) != ranking(computed):
            raise ResearchAuditError(f"saved descriptive ranking differs in {section}")
    # A last-bit change at a decimal rounding tie can change displayed .1%.
    # Preserve the reviewed saved numeric representation after its strict audit.
    if (study_dir / "FINDINGS.md").read_bytes() != _markdown(saved).encode("utf-8"):
        raise ResearchAuditError("saved FINDINGS.md differs from audited findings")
    return saved, {
        "status": "passed", "derived_float_differences": differences,
        "maximum_absolute_difference": max((item["absolute_difference"] for item in differences), default=0.0),
        "absolute_rounding_limit": MAX_ABSOLUTE_ROUNDING,
        "discrete_values_and_types_exact": True, "rendered_markdown_exact": True,
        "canonical_json_exact": True, "derived_signs_and_descriptive_rankings_exact": True,
    }


def verify_research(study_dir: Path = DEFAULT_STUDY) -> tuple[dict, dict]:
    # This retains every source, manifest, raw row, selection and schedule check.
    return verify_saved(study_dir, analyze_study(study_dir, write=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY)
    args = parser.parse_args()
    saved, receipt = verify_research(args.study_dir)
    print(f"Verified {saved['total_games']} games across {len(saved['stages'])} stages; "
          f"{len(receipt['derived_float_differences'])} bounded rounding differences, "
          f"maximum {receipt['maximum_absolute_difference']:.17g}; exact discrete evidence and Markdown")


if __name__ == "__main__":
    main()
