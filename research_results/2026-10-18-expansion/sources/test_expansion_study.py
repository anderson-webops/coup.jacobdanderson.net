"""Expansion protocol, schedule, raw-data and block-inference regressions."""
from __future__ import annotations

from collections import Counter
import copy
import csv
import gzip
import io
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import expansion_study as study
from expansion_statistics import ExpansionDataError, paired_compare, panel


def outcome_rows(players=10, blocks=4, first="first", second="second"):
    rows = []
    for candidate in (first, second):
        for block in range(blocks):
            for rotation in range(players):
                winner = rotation if candidate == first else (rotation + 1) % players
                rows.append({"candidate": candidate, "block": block, "rotation": rotation,
                    "seed": 100 + block, "focal_seat": rotation, "winner": winner,
                    "won": int(winner == rotation), "draw": 0, "turns": 12})
    return rows


class ExpansionBlockStatisticsTests(unittest.TestCase):
    def test_ten_players_complete_rotation_and_conservative_interval(self):
        result = paired_compare(outcome_rows(), 10, "first", "second", 4, 135)
        self.assertEqual((result["first_wins"], result["second_wins"]), (40, 0))
        self.assertEqual(result["difference"], 1)
        self.assertEqual(result["normal_family_lower"], 1)
        self.assertLess(result["conservative_family_lower"], 0)

    def test_duplicate_missing_and_inconsistent_winner_rejected(self):
        rows = outcome_rows()
        for changed in (rows + [rows[0]], rows[1:]):
            with self.assertRaises(ExpansionDataError):
                panel(changed, 10, ("first", "second"), 4)
        rows[0]["won"] = 0
        with self.assertRaises(ExpansionDataError):
            panel(rows, 10, ("first", "second"), 4)

    def test_candidate_seed_mismatch_and_seed_reuse_rejected(self):
        rows = outcome_rows()
        for row in rows:
            if row["candidate"] == "second" and row["block"] == 0:
                row["seed"] = 9876
        with self.assertRaises(ExpansionDataError):
            panel(rows, 10, ("first", "second"), 4)
        for row in rows:
            row["seed"] = 100
        with self.assertRaises(ExpansionDataError):
            panel(rows, 10, ("first", "second"), 4)

    def test_draws_remain_in_denominator(self):
        rows = outcome_rows(players=2)
        for row in rows:
            if row["block"] == 0:
                row.update(winner="", won=0, draw=1)
        result = paired_compare(rows, 2, "first", "second", 4, 1)
        self.assertEqual(result["first_rate"], .75)
        self.assertEqual(result["first_draws"], 2)
        self.assertEqual(result["second_draws"], 2)

    def test_boolean_integer_and_invalid_inference_rejected(self):
        rows = outcome_rows()
        rows[0]["block"] = False
        with self.assertRaises(ExpansionDataError):
            panel(rows, 10, ("first", "second"), 4)
        with self.assertRaises(ExpansionDataError):
            paired_compare(outcome_rows(), 10, "first", "second", 4, 0)


class FakeGame:
    """Deterministic scheduling fixture; it makes no claims about game rules."""
    def __init__(self, n, seed, policies, profile, max_turns, strict, record, identities):
        self.n, self.seed, self.names, self.identities = n, seed, policies, identities
        self.turn = 3 + seed % 7
        self.diagnostics = Counter(action_income=self.turn)
        if not strict or record or max_turns != 1000 or sorted(identities) != list(range(n)):
            raise AssertionError("runner did not request the frozen strict game configuration")

    def run(self):
        # Identity-dependent choice catches rotation attribution and repeated names.
        winner_identity = (self.seed + sum(study.POLICIES.index(p) for p in self.names)) % self.n
        return self.identities.index(winner_identity)

    def check_invariants(self):
        # The scheduling fixture deliberately has no cards or game mechanics.
        return None


class ExpansionProtocolTests(unittest.TestCase):
    def setUp(self):
        scratch = study.ROOT / ".ai-work" / "runs" / "20261018-expansion"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="study-test-", dir=scratch)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in study.SOURCE_FILES:
            (self.root / name).write_text(f"# Frozen protocol test source: {name}\n")
        self.root_patch = patch.object(study, "ROOT", self.root)
        self.root_patch.start(); self.addCleanup(self.root_patch.stop)
        self.config_patch = patch.object(study, "_configuration_catalogue", return_value={p: {"name": p} for p in study.POLICIES})
        self.config_patch.start(); self.addCleanup(self.config_patch.stop)
        self.game_patch = patch.dict(sys.modules, {"expansion_simulator": SimpleNamespace(ExpansionGame=FakeGame)})
        self.game_patch.start(); self.addCleanup(self.game_patch.stop)
        self.directory = self.root / "research_results" / "study"

    def freeze(self, directory=None):
        return study.freeze_plan(directory or self.directory, screen_blocks=2,
            confirmation_blocks=2, counter_search_blocks=2, counter_blocks=2)

    def first_stage(self):
        plan = self.freeze()
        jobs = [study._screen_jobs(plan)[0]]
        study._run_stage(self.directory, "screening", jobs, 1)
        return jobs

    def test_freeze_has_no_outcomes_and_resume_requires_exact_counts(self):
        plan = self.freeze()
        self.assertEqual(study._check_plan(self.directory), plan)
        self.assertEqual({p.name for p in self.directory.iterdir()}, {"plan.json", "preregistration.json", "sources"})
        self.assertEqual(self.freeze(), plan)
        with self.assertRaises(study.ExpansionStudyError):
            study.freeze_plan(self.directory, screen_blocks=3, confirmation_blocks=2,
                counter_search_blocks=2, counter_blocks=2)

    def test_execution_source_and_snapshot_drift_rejected(self):
        self.freeze()
        path = self.root / study.SOURCE_FILES[0]
        original = path.read_bytes(); path.write_bytes(original + b"# drift\n")
        with self.assertRaises(study.ExpansionStudyError):
            study._check_plan(self.directory)
        path.write_bytes(original)
        snapshot = self.directory / "sources" / study.SOURCE_FILES[0]
        snapshot.write_bytes(original + b"# drift\n")
        with self.assertRaises(study.ExpansionStudyError):
            study._check_plan(self.directory)

    def test_plan_change_breaks_local_preregistration_receipt(self):
        self.freeze()
        path = self.directory / "plan.json"
        plan = study.read_json(path)
        plan["blocks"]["confirmation"] = 3
        path.write_bytes(study.json_bytes(plan))
        with self.assertRaises(study.ExpansionStudyError):
            study._check_plan(self.directory)

    def test_seed_namespaces_do_not_overlap(self):
        seeds = [study.seed_for(profile, stage, n, field, block)
            for profile in study.PROFILES for stage in study.STAGES for n in range(2, 11)
            for field in study.FIELDS for block in range(3)]
        self.assertEqual(len(seeds), len(set(seeds)))

    def test_focal_identity_and_repeated_policy_rosters(self):
        for n in range(2, 11):
            for rotation in range(n):
                names, identities = study.roster(n, "honest", "honest", 0, rotation)
                self.assertEqual(names, ["honest"] * n)
                self.assertEqual(identities[rotation], 0)
                self.assertEqual(sorted(identities), list(range(n)))
        forward, _ = study.roster(10, "honest", "mixed", 0, 0)
        reverse, _ = study.roster(10, "honest", "mixed", 8, 0)
        self.assertEqual(forward[1:], list(reversed(reverse[1:])))

    def test_selection_uses_all_fields_and_lexical_ties(self):
        rows = [{"profile": profile, "players": n, "field": field, "candidate": p, "wins": 0}
            for profile in study.PROFILES for n in range(2, 11) for field in study.FIELDS for p in study.POLICIES]
        selected = study.select_finalists(rows)
        self.assertTrue(all(r["first"] == "balanced" and r["second"] == "bluff" for r in selected["finalists"]))
        rows[0]["wins"] = 100
        self.assertEqual(study.select_finalists(rows)["finalists"][0]["first"], "honest")

    def test_deterministic_compression_and_resume(self):
        jobs = self.first_stage()
        path = self.directory / "screening" / study._filename(jobs[0])
        first = path.read_bytes()
        study._run_job(self.directory, "screening", jobs[0])
        self.assertEqual(path.read_bytes(), first)
        second = self.root / "research_results" / "second"
        plan = self.freeze(second)
        study._run_stage(second, "screening", [study._screen_jobs(plan)[0]], 1)
        self.assertEqual((second / "screening" / path.name).read_bytes(), first)

    def test_manifest_inventory_and_symlinks_rejected(self):
        jobs = self.first_stage()
        extra = self.directory / "screening" / "unexpected.txt"
        extra.write_text("extra")
        with self.assertRaises(study.ExpansionStudyError):
            study.audit_stage(self.directory, "screening", jobs)
        extra.unlink()
        raw = self.directory / "screening" / study._filename(jobs[0])
        kept = self.directory / "raw-copy"
        kept.write_bytes(raw.read_bytes()); raw.unlink(); raw.symlink_to(kept)
        with self.assertRaises(study.ExpansionStudyError):
            study.audit_stage(self.directory, "screening", jobs)

    def test_raw_tamper_and_cached_summary_tamper_rejected(self):
        jobs = self.first_stage()
        raw = self.directory / "screening" / study._filename(jobs[0])
        diagnostic = raw.with_suffix(".diagnostics.json")
        record = study.read_json(diagnostic)
        record["summary"]["wins"] += 1
        diagnostic.write_bytes(study.json_bytes(record))
        with self.assertRaises(study.ExpansionStudyError):
            study._run_job(self.directory, "screening", jobs[0])
        with self.assertRaises(study.ExpansionStudyError):
            study.audit_stage(self.directory, "screening", jobs)

    def test_wrong_raw_seed_rejected_even_if_output_hashes_are_updated(self):
        jobs = self.first_stage()
        raw = self.directory / "screening" / study._filename(jobs[0])
        rows = list(study._raw_rows(raw))
        rows[0]["seed"] = "0"
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=study.RAW_COLUMNS)
        writer.writeheader(); writer.writerows(rows)
        raw.write_bytes(gzip.compress(output.getvalue().encode(), mtime=0))
        diagnostic = raw.with_suffix(".diagnostics.json")
        record = study.read_json(diagnostic)
        record["raw_sha256"] = study.digest(raw)
        diagnostic.write_bytes(study.json_bytes(record))
        manifest_path = raw.parent / "manifest.json"
        manifest = study.read_json(manifest_path)
        manifest["files"][raw.name] = study.digest(raw)
        manifest["files"][diagnostic.name] = study.digest(diagnostic)
        manifest_path.write_bytes(study.json_bytes(manifest))
        with self.assertRaises(study.ExpansionStudyError):
            study.audit_stage(self.directory, "screening", jobs)

    def test_optimized_python_rejected_before_evidence_is_read(self):
        result = subprocess.run([sys.executable, "-O", "-B", "-c",
            "import expansion_study; expansion_study.verify_study('missing')"],
            capture_output=True, text=True, cwd=Path(__file__).resolve().parent)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("optimized Python is not allowed", result.stderr)

    def test_complete_four_stage_pipeline_and_findings_audit(self):
        self.freeze()
        findings = study.run_study(self.directory, workers=1)
        self.assertEqual(findings["total_games"], 16920)
        self.assertEqual(len(findings["confirmation_pairs"]), 135)
        self.assertEqual(len(findings["counters"]), 6)
        self.assertEqual(len(findings["recommendations"]), 54)
        self.assertEqual(study.verify_study(self.directory), findings)
        from audit_expansion_research import audit
        receipt = audit(self.directory, source_root=self.root, game_class=FakeGame)
        self.assertEqual(receipt["total_raw_games"], 16920)
        self.assertEqual(receipt["total_replayed_games"], 16920)
        extra = self.directory / "unexpected.txt"
        extra.write_text("unreviewed root content")
        with self.assertRaises(study.ExpansionStudyError):
            study.verify_study(self.directory)
        extra.unlink()
        saved_path = self.directory / "findings.json"
        changed = copy.deepcopy(findings)
        changed["confirmation_pairs"][0]["difference"] += .01
        saved_path.write_bytes(study.json_bytes(changed))
        with self.assertRaises(study.ExpansionStudyError):
            study.verify_study(self.directory)

    def test_derived_float_tolerance_is_narrow(self):
        first = {"confirmation_pairs": [{"normal_family_lower": .2, "first_rate": .25}]}
        second = copy.deepcopy(first)
        second["confirmation_pairs"][0]["normal_family_lower"] += 1e-15
        study._compare_saved(first, second)
        second["confirmation_pairs"][0]["first_rate"] += 1e-15
        with self.assertRaises(study.ExpansionStudyError):
            study._compare_saved(first, second)

    def test_duplicate_json_keys_rejected(self):
        self.directory.mkdir(parents=True)
        path = self.directory / "duplicate.json"
        path.write_text('{"a":1,"a":2}\n')
        with self.assertRaises(study.ExpansionStudyError):
            study.read_json(path)


if __name__ == "__main__":
    unittest.main()
