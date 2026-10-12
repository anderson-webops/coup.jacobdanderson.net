"""Independent checks for paired Coup research summaries."""
import copy
import math
import unittest

from research_statistics import StudyDataError, audit_panel, paired_compare


def panel(blocks=40, players=3):
    """Construct matched CSV-shaped rows with one identity per focal seat."""
    rows = []
    for block in range(blocks):
        for candidate in ("candidate_a", "candidate_b"):
            for rotation in range(players):
                focal_seat = (rotation + block) % players
                # A wins two seats in three quarters of blocks; B wins one
                # seat in half the blocks. A draw is still a scheduled game.
                if candidate == "candidate_a":
                    win = block % 4 != 0 and rotation < 2
                else:
                    win = block % 2 == 0 and rotation == 0
                draw = candidate == "candidate_a" and block == 0 and rotation == 1
                winner = "" if draw else focal_seat if win else (focal_seat + 1) % players
                rows.append({
                    "stage": "confirmation", "players": str(players),
                    "field": "belief", "candidate": candidate,
                    "block": str(block), "rotation": str(rotation),
                    "seed": str(900000 + block),
                    "winner": str(winner) if winner != "" else "",
                    "focal_seat": str(focal_seat), "won": str(int(win)),
                    "draw": str(int(draw)), "turns": "19",
                })
    return rows


class ResearchStatisticsTests(unittest.TestCase):
    def test_paired_block_rates_and_draw_denominator(self):
        result = paired_compare(panel(), 3, "belief", "candidate_a", "candidate_b")
        self.assertEqual(result["blocks"], 40)
        self.assertEqual(result["games_per_candidate"], 120)
        self.assertEqual(result["first_wins"], 60)
        self.assertEqual(result["second_wins"], 20)
        self.assertEqual(result["first_draws"], 1)
        self.assertAlmostEqual(result["first_rate"], 0.5)
        self.assertAlmostEqual(result["second_rate"], 1 / 6)
        self.assertAlmostEqual(result["difference"], 1 / 3)
        self.assertLess(result["conservative_family_lower"], result["normal_family_lower"])

    def test_family_size_widens_normal_and_conservative_bounds(self):
        rows = panel()
        narrow = paired_compare(rows, 3, "belief", "candidate_a", "candidate_b", family_size=1)
        wide = paired_compare(rows, 3, "belief", "candidate_a", "candidate_b", family_size=30)
        self.assertLess(wide["normal_family_lower"], narrow["normal_family_lower"])
        self.assertLess(wide["conservative_family_lower"], narrow["conservative_family_lower"])

    def test_swapped_candidates_reverse_paired_difference(self):
        rows = panel()
        ab = paired_compare(rows, 3, "belief", "candidate_a", "candidate_b")
        ba = paired_compare(rows, 3, "belief", "candidate_b", "candidate_a")
        self.assertAlmostEqual(ab["difference"], -ba["difference"])
        self.assertAlmostEqual(ab["normal_family_lower"], -ba["normal_family_upper"])

    def test_rejects_duplicate_missing_or_unbalanced_rotation(self):
        rows = panel()
        with self.assertRaisesRegex(StudyDataError, "duplicate"):
            paired_compare(rows + [copy.copy(rows[0])], 3, "belief", "candidate_a", "candidate_b")
        with self.assertRaisesRegex(StudyDataError, "incomplete rotation"):
            paired_compare(rows[1:], 3, "belief", "candidate_a", "candidate_b")
        changed = copy.deepcopy(rows)
        changed[1]["focal_seat"] = changed[0]["focal_seat"]
        changed[1]["winner"] = "2"
        changed[1]["won"] = "0"
        changed[1]["draw"] = "0"
        with self.assertRaisesRegex(StudyDataError, "focal seats"):
            paired_compare(changed, 3, "belief", "candidate_a", "candidate_b")

    def test_rejects_seed_and_outcome_corruption(self):
        rows = panel()
        changed = copy.deepcopy(rows)
        changed[1]["seed"] = "123"
        with self.assertRaisesRegex(StudyDataError, "multiple initial seeds"):
            paired_compare(changed, 3, "belief", "candidate_a", "candidate_b")
        changed = copy.deepcopy(rows)
        changed[3]["seed"] = "777"
        changed[4]["seed"] = "777"
        changed[5]["seed"] = "777"
        with self.assertRaisesRegex(StudyDataError, "seed or focal seat"):
            paired_compare(changed, 3, "belief", "candidate_a", "candidate_b")
        changed = copy.deepcopy(rows)
        changed[0]["won"] = "1"
        with self.assertRaisesRegex(StudyDataError, "won/draw"):
            paired_compare(changed, 3, "belief", "candidate_a", "candidate_b")

    def test_rejects_insufficient_blocks_and_invalid_family(self):
        with self.assertRaisesRegex(StudyDataError, "need at least"):
            paired_compare(panel(blocks=29), 3, "belief", "candidate_a", "candidate_b")
        with self.assertRaises(ValueError):
            paired_compare(panel(), 3, "belief", "candidate_a", "candidate_b", family_size=0)
        with self.assertRaises(ValueError):
            paired_compare(panel(), 3, "belief", "candidate_a", "candidate_b", alpha=math.nan)

    def test_audit_requires_exact_frozen_roster_and_block_ids(self):
        rows = panel()
        report = audit_panel(rows, 3, "belief", ("candidate_a", "candidate_b"), 40)
        self.assertEqual(report["games_per_candidate"], 120)
        self.assertEqual(report["wins"]["candidate_a"], 60)
        with self.assertRaisesRegex(StudyDataError, "candidate roster"):
            audit_panel(rows, 3, "belief", ("candidate_a",), 40)
        without_last_block = [row for row in rows if row["block"] != "39"]
        with self.assertRaisesRegex(StudyDataError, "exact planned block"):
            audit_panel(without_last_block, 3, "belief", ("candidate_a", "candidate_b"), 40)
        with self.assertRaisesRegex(StudyDataError, "exact planned block"):
            paired_compare(without_last_block, 3, "belief", "candidate_a", "candidate_b",
                           expected_blocks=40)


if __name__ == "__main__":
    unittest.main()
