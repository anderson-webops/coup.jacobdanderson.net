"""Portability checks preserve discrete evidence and canonical publication."""
import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

from analyze_strategy_research import DEFAULT_STUDY, ResearchAuditError, _markdown
from verify_strategy_research import compare_findings, verify_saved


class PortableResearchTests(unittest.TestCase):
    def test_exact_and_bounded_derived_values(self):
        a = {"confirmation_pairs": [{"difference": 0.1}],
             "equal_field_robustness": [{"equal_field_mean": 0.4}]}
        b = copy.deepcopy(a)
        b["confirmation_pairs"][0]["difference"] += 1e-15
        b["equal_field_robustness"][0]["equal_field_mean"] += 1e-15
        self.assertEqual(compare_findings(a, a), [])
        self.assertEqual(len(compare_findings(a, b)), 2)

    def test_numeric_drift_is_rejected(self):
        for a, b in [(0.1, 0.1 + 1e-12), (1e-16, -1e-16), (0.0, 1e-16), (-0.0, 0.0)]:
            with self.subTest(a=a, b=b), self.assertRaises(ResearchAuditError):
                compare_findings({"counters": [{"difference": a}]},
                                 {"counters": [{"difference": b}]})

    def test_direct_rates_and_unlisted_float_paths_stay_exact(self):
        for a, b in [({"counters": [{"first_rate": 0.1}]},
                      {"counters": [{"first_rate": math.nextafter(0.1, 1.0)}]}),
                     ({"nested": {"difference": 0.1}},
                      {"nested": {"difference": math.nextafter(0.1, 1.0)}})]:
            with self.subTest(a=a), self.assertRaises(ResearchAuditError):
                compare_findings(a, b)

    def test_types_are_exact(self):
        for a, b in [(1, True), (1, 1.0), (False, 0), ([], ())]:
            with self.subTest(a=a, b=b), self.assertRaises(ResearchAuditError):
                compare_findings(a, b)

    def test_nonfinite_floats_are_rejected_even_if_equal(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(ResearchAuditError):
                compare_findings({"counters": [{"difference": value}]},
                                 {"counters": [{"difference": value}]})

    def test_structure_and_list_order_stay_exact(self):
        for a, b in [({"x": 1}, {}), ({}, {"x": 1}),
                     ([1, 2], [1]), ([1, 2], [2, 1])]:
            with self.subTest(a=a, b=b), self.assertRaises(ResearchAuditError):
                compare_findings(a, b)

    def test_counts_flags_selections_and_hashes_stay_exact(self):
        for key, a, b in [("wins", 100, 101), ("normal_supports_positive", True, False),
                          ("first", "baseline", "exchange"),
                          ("global_plan_sha256", "abc", "def")]:
            with self.subTest(key=key), self.assertRaises(ResearchAuditError):
                compare_findings({key: a}, {key: b})

    def test_canonical_rounding_tie_preserves_saved_markdown(self):
        saved = json.loads((DEFAULT_STUDY / "findings.json").read_bytes())
        computed = copy.deepcopy(saved)
        row = next(row for row in computed["confirmation_pairs"]
                   if row["players"] == 6 and row["field"] == "mixed")
        row["difference"] = 0.0205
        self.assertNotEqual(_markdown(saved), _markdown(computed))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "findings.json").write_text(json.dumps(saved, indent=2, sort_keys=True) + "\n")
            (root / "FINDINGS.md").write_text(_markdown(saved))
            canonical, receipt = verify_saved(root, computed)
            self.assertEqual(canonical, saved)
            self.assertTrue(receipt["rendered_markdown_exact"])

    def test_changed_markdown_is_rejected(self):
        saved = json.loads((DEFAULT_STUDY / "findings.json").read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "findings.json").write_text(json.dumps(saved, indent=2, sort_keys=True) + "\n")
            (root / "FINDINGS.md").write_text(_markdown(saved) + "changed")
            with self.assertRaisesRegex(ResearchAuditError, "FINDINGS.md"):
                verify_saved(root, saved)

    def test_duplicate_saved_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "findings.json").write_text('{"wins":1,"wins":1}')
            with self.assertRaisesRegex(ResearchAuditError, "duplicate"):
                verify_saved(root, {"wins": 1})

    def test_canonical_encoding_and_descriptive_rankings_are_enforced(self):
        saved = json.loads((DEFAULT_STUDY / "findings.json").read_bytes())
        same_players = [row for row in saved["equal_field_robustness"] if row["players"] == 2]
        same_players[0]["equal_field_mean"] = 0.3
        same_players[1]["equal_field_mean"] = math.nextafter(0.3, 1.0)
        computed = copy.deepcopy(saved)
        first = next(row for row in computed["equal_field_robustness"]
                     if row["players"] == 2 and row["candidate"] == same_players[0]["candidate"])
        first["equal_field_mean"] = math.nextafter(same_players[1]["equal_field_mean"], 1.0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "FINDINGS.md").write_text(_markdown(saved))
            (root / "findings.json").write_text(json.dumps(saved))
            with self.assertRaisesRegex(ResearchAuditError, "canonical"):
                verify_saved(root, saved)
            (root / "findings.json").write_text(json.dumps(saved, indent=2, sort_keys=True) + "\n")
            with self.assertRaisesRegex(ResearchAuditError, "ranking"):
                verify_saved(root, computed)


if __name__ == "__main__":
    unittest.main()
