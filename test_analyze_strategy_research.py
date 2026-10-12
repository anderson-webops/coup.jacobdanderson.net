"""Independent, small fixtures for provenance and raw-result reconciliation."""
from __future__ import annotations

import csv
import gzip
import io
import json
import tempfile
import unittest
from pathlib import Path

from analyze_strategy_research import (PROJECT, RAW_COLUMNS, SUMMARY_COLUMNS,
                                       ResearchAuditError, STAGES, _markdown,
                                       _verify_saved_findings, audit_stage, digest)


def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def raw_file(path: Path, rows: list[dict]) -> None:
    with path.open("wb") as output:
        with gzip.GzipFile(filename="", fileobj=output, mode="wb", mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text:
                writer = csv.DictWriter(text, fieldnames=RAW_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)


class AuditStageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.study = Path(self.temp.name)
        self.stage = self.study / "confirmation"
        self.stage.mkdir()
        self.global_plan = {"source_sha256": {
            "research_statistics.py": digest(PROJECT / "research_statistics.py")}}
        save_json(self.study / "plan.json", self.global_plan)
        self.jobs = [{"players": 2, "field": "honest", "candidate": name, "blocks": 3}
                     for name in ("alpha", "beta")]
        self.plan = {"stage": "confirmation", "jobs": self.jobs,
                     "fields": ["honest"], "pairs": [], "extra": {},
                     "global_plan_sha256": digest(self.study / "plan.json"),
                     "source_sha256": self.global_plan["source_sha256"]}
        save_json(self.stage / "plan.json", self.plan)
        summaries = []
        all_seats = {}
        for job in self.jobs:
            candidate = job["candidate"]
            rows = []
            seats = {str(i): {"wins": 0, "draws": 0, "games": 0} for i in range(2)}
            for block in range(3):
                seed = 202610120000000 + 2 * 10**12 + 2 * 10**9 + block
                for rotation in range(2):
                    winner = (block + (candidate == "beta")) % 2
                    won = int(winner == rotation)
                    rows.append({"stage": "confirmation", "players": 2,
                                 "field": "honest", "candidate": candidate,
                                 "block": block, "rotation": rotation, "seed": seed,
                                 "winner": winner, "focal_seat": rotation,
                                 "won": won, "draw": 0, "turns": 20})
                    seats[str(rotation)]["wins"] += won
                    seats[str(rotation)]["games"] += 1
            name = f"2-honest-{candidate}.csv.gz"
            raw_file(self.stage / name, rows)
            summary = {"stage": "confirmation", "players": 2, "field": "honest",
                       "candidate": candidate, "games": 6, "wins": 3, "draws": 0,
                       "win_rate": .5, "mean_turns": 20.0, "blocks": 3}
            summaries.append(summary)
            save_json(self.stage / name.replace(".gz", ".diagnostics.json"),
                      {"stage": "confirmation", "job": job,
                       "raw_sha256": digest(self.stage / name), "summary": summary,
                       "actions": {}, "events": {}, "seats": seats})
            all_seats[name] = seats
        with (self.stage / "summaries.csv").open("w", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=SUMMARY_COLUMNS)
            writer.writeheader()
            writer.writerows(summaries)
        save_json(self.stage / "diagnostics.json", {
            "actions": {}, "events": {}, "games": 12, "draws": 0,
            "seats": all_seats})
        self.resign()

    def resign(self) -> None:
        files = {path.name: digest(path) for path in self.stage.iterdir()
                 if path.is_file() and path.name != "manifest.json"}
        save_json(self.stage / "manifest.json", {
            "stage": "confirmation", "files": files,
            "plan_sha256": digest(self.stage / "plan.json"),
            "global_plan_sha256": digest(self.study / "plan.json"),
            "source_sha256": self.global_plan["source_sha256"],
            "scheduled_games": 12})

    def test_complete_panel_and_diagnostics(self) -> None:
        result = audit_stage(self.study, "confirmation")
        self.assertEqual((result["games"], result["wins"], result["draws"]), (12, 6, 0))
        self.assertEqual(result["jobs"], 2)

    def test_missing_rotation_rejected_after_resigning(self) -> None:
        path = self.stage / "2-honest-alpha.csv.gz"
        with gzip.open(path, "rt", newline="") as source:
            rows = list(csv.DictReader(source))
        raw_file(path, rows[:-1])
        diagnostic = self.stage / "2-honest-alpha.csv.diagnostics.json"
        item = json.loads(diagnostic.read_text())
        item["raw_sha256"] = digest(path)
        save_json(diagnostic, item)
        self.resign()
        with self.assertRaisesRegex(ResearchAuditError, "raw game count"):
            audit_stage(self.study, "confirmation")

    def test_changed_raw_hash_rejected(self) -> None:
        with (self.stage / "2-honest-alpha.csv.gz").open("ab") as output:
            output.write(b"extra")
        with self.assertRaisesRegex(ResearchAuditError, "output hash"):
            audit_stage(self.study, "confirmation")

    def test_summary_mismatch_rejected_after_resigning(self) -> None:
        path = self.stage / "summaries.csv"
        text = path.read_text()
        path.write_text(text.replace("alpha,6,3,0", "alpha,6,4,0"))
        self.resign()
        with self.assertRaisesRegex(ResearchAuditError, "summary counts"):
            audit_stage(self.study, "confirmation")

    def test_seat_diagnostic_mismatch_rejected_after_resigning(self) -> None:
        path = self.stage / "2-honest-alpha.csv.diagnostics.json"
        item = json.loads(path.read_text())
        item["seats"]["0"]["wins"] += 1
        save_json(path, item)
        self.resign()
        with self.assertRaisesRegex(ResearchAuditError, "seats differ"):
            audit_stage(self.study, "confirmation")

    def test_missing_companion_file_rejected(self) -> None:
        (self.stage / "2-honest-alpha.csv.diagnostics.json").unlink()
        self.resign()
        with self.assertRaisesRegex(ResearchAuditError, "inventory differs"):
            audit_stage(self.study, "confirmation")

    def test_source_fingerprint_rejected(self) -> None:
        self.global_plan["source_sha256"]["research_statistics.py"] = "0" * 64
        save_json(self.study / "plan.json", self.global_plan)
        with self.assertRaisesRegex(ResearchAuditError, "source changed"):
            audit_stage(self.study, "confirmation")

    def test_seed_formula_rejected_after_resigning(self) -> None:
        path = self.stage / "2-honest-alpha.csv.gz"
        with gzip.open(path, "rt", newline="") as source:
            rows = list(csv.DictReader(source))
        rows[0]["seed"] = str(int(rows[0]["seed"]) + 1)
        raw_file(path, rows)
        diagnostic = self.stage / "2-honest-alpha.csv.diagnostics.json"
        item = json.loads(diagnostic.read_text())
        item["raw_sha256"] = digest(path)
        save_json(diagnostic, item)
        self.resign()
        with self.assertRaisesRegex(ResearchAuditError, "seed or rotation"):
            audit_stage(self.study, "confirmation")

    def test_saved_findings_must_match_recomputed_json_and_markdown(self) -> None:
        findings = {"stages": {stage: {"games": 0, "draws": 0, "jobs": 0}
                               for stage in STAGES},
                    "confirmation_pairs": [], "observed_leaders": [],
                    "limitations": []}
        save_json(self.study / "findings.json", findings)
        (self.study / "FINDINGS.md").write_text(_markdown(findings))
        _verify_saved_findings(self.study, findings)
        wrong = findings | {"total_games": 1}
        with self.assertRaisesRegex(ResearchAuditError, "findings.json differs"):
            _verify_saved_findings(self.study, wrong)
        (self.study / "FINDINGS.md").write_text("stale report\n")
        with self.assertRaisesRegex(ResearchAuditError, "FINDINGS.md differs"):
            _verify_saved_findings(self.study, findings)

    def test_missing_saved_findings_rejected(self) -> None:
        with self.assertRaisesRegex(ResearchAuditError, "cannot read JSON"):
            _verify_saved_findings(self.study, {})


if __name__ == "__main__":
    unittest.main()
