"""Independent expansion evidence audit rejection and replay checks."""
from __future__ import annotations

import json
import csv
import gzip
import hashlib
from pathlib import Path
import tempfile
import unittest

import audit_expansion_research as audit


class ExpansionAuditUtilityTests(unittest.TestCase):
    def test_integer_rejects_ambiguous_and_noncanonical_values(self):
        for value in (True, False, 1., None, "01", "+1", "-1", " 1", "١", "1.0"):
            with self.subTest(value=value), self.assertRaises(audit.ExpansionAuditError):
                audit.integer(value, "sample")
        self.assertEqual(audit.integer("0", "sample"), 0)
        self.assertEqual(audit.integer(7, "sample", maximum=7), 7)
        with self.assertRaises(audit.ExpansionAuditError):
            audit.integer(8, "sample", maximum=7)

    def test_sample_covers_complete_first_middle_last_blocks(self):
        self.assertEqual(audit.sample_blocks(1), [0])
        self.assertEqual(audit.sample_blocks(2), [0, 1])
        self.assertEqual(audit.sample_blocks(1000), [0, 500, 999])
        with self.assertRaises(audit.ExpansionAuditError):
            audit.sample_blocks(0)

    def test_json_rejects_duplicate_keys_and_nonfinite_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "plan.json"
            for text in ('{"x": 1, "x": 2}', '{"x": NaN}', '{"x": Infinity}'):
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(audit.ExpansionAuditError):
                    audit.read_json(path)
            path.write_bytes(audit.json_bytes({"x": [1, 2]}))
            self.assertEqual(audit.read_json(path), {"x": [1, 2]})

    def test_hash_rejects_symlink_and_missing_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "source.py"
            path.write_bytes(b"source")
            self.assertEqual(audit.sha256(path),
                             "41cf6794ba4200b839c53531555f0f3998df4cbb01a4d5cb0b94e3ca5e23947d")
            linked = root / "linked.py"
            linked.symlink_to(path)
            for rejected in (linked, root / "absent.py", root):
                with self.subTest(path=rejected), self.assertRaises(audit.ExpansionAuditError):
                    audit.sha256(rejected)


class FakeStrictGame:
    calls = []

    def __init__(self, players, *, seed, policies, profile, identities, max_turns, strict, record):
        if strict is not True or record is not False or max_turns != 1000:
            raise AssertionError("Audit did not request strict production settings")
        if set(identities) != set(range(players)) or len(policies) != players:
            raise AssertionError("Invalid replay identities")
        self.players, self.seed, self.turn = players, seed, seed % 7 + 1
        self.calls.append((players, seed, tuple(policies), tuple(identities), profile))

    def run(self):
        return self.seed % self.players

    def check_invariants(self):
        self.calls.append("invariants checked")


def save_json(path, value):
    path.write_bytes(audit.json_bytes(value))


def fixture_stage(root, *, block_count=4):
    """Write raw rows directly, without importing a runner or its helpers."""
    save_json(root / "plan.json", {"local": "fixture"})
    stage = root / "screening"
    stage.mkdir()
    item = {"profile": "combined", "players": 3, "field": "mixed", "candidate": "honest", "blocks": block_count}
    plan = {"source_sha256": {"fixture.py": "a" * 64}}
    stage_plan = {"stage": "screening", "source_sha256": plan["source_sha256"],
                  "global_plan_sha256": audit.sha256(root / "plan.json"), "jobs": [item]}
    save_json(stage / "plan.json", stage_plan)
    rows = []
    for block in range(block_count):
        coordinate = f"coup-expansion-study-v1:combined:screening:3:mixed:{block}"
        seed = int.from_bytes(hashlib.sha256(coordinate.encode("ascii")).digest(), "big")
        for rotation in range(3):
            winner = seed % 3
            rows.append(dict(zip(audit.RAW_COLUMNS, ("combined", "screening", "3", "mixed", "honest", str(block),
                str(rotation), str(seed), str(winner), str(rotation), str(int(winner == rotation)), "0", str(seed % 7 + 1)))))
    raw = stage / audit.filename(item)
    write_rows(raw, rows)
    sync_stage(root, plan, item)
    return plan, item, raw, rows


def write_rows(path, rows):
    with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=audit.RAW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def sync_stage(root, plan, item):
    stage = root / "screening"
    raw = stage / audit.filename(item)
    summary, _ = audit.read_raw(raw, "screening", item, audit.sha256(raw))
    save_json(raw.with_suffix(".diagnostics.json"), {"stage": "screening", "job": item, "summary": summary,
        "raw_sha256": audit.sha256(raw), "diagnostics": {"actions": 12}})
    with (stage / "summaries.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=audit.SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(summary)
    rehash_stage(root, plan, item)


def rehash_stage(root, plan, item):
    stage = root / "screening"
    files = {p.name: audit.sha256(p) for p in stage.iterdir() if p.name != "manifest.json"}
    save_json(stage / "manifest.json", {"stage": "screening", "source_sha256": plan["source_sha256"],
        "global_plan_sha256": audit.sha256(root / "plan.json"), "plan_sha256": audit.sha256(stage / "plan.json"),
        "scheduled_games": item["players"] * item["blocks"], "files": files})


class ExpansionAuditRawTests(unittest.TestCase):
    def test_raw_summary_and_all_rotations_replay_independently(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan, item, raw, rows = fixture_stage(root)
            FakeStrictGame.calls = []
            receipt, summaries = audit.audit_stage(root, plan, "screening", [item], FakeStrictGame)
            self.assertEqual(receipt["raw_games"], 12)
            self.assertEqual(receipt["replayed_games"], 9)
            self.assertEqual(summaries[0]["wins"], 4)
            self.assertEqual(summaries[0]["draws"], 0)
            self.assertEqual(FakeStrictGame.calls.count("invariants checked"), 9)
            self.assertEqual({call[3].index(0) for call in FakeStrictGame.calls if call != "invariants checked"}, {0, 1, 2})

    def test_all_raw_coordinate_and_outcome_corruption_is_rejected(self):
        changes = (("profile", "inquisitor"), ("stage", "confirmation"), ("players", "2"),
                   ("candidate", "bluff"), ("field", "adaptive"), ("block", "4"),
                   ("rotation", "3"), ("seed", "1"), ("winner", "3"), ("focal_seat", "1"),
                   ("won", "2"), ("draw", "1"), ("turns", "0"), ("turns", "1001"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, item, raw, original = fixture_stage(root)
            for key, value in changes:
                rows = [dict(row) for row in original]
                rows[0][key] = value
                write_rows(raw, rows)
                with self.subTest(key=key, value=value), self.assertRaises(audit.ExpansionAuditError):
                    audit.read_raw(raw, "screening", item, audit.sha256(raw))
            for rows in (original[:-1], original + original[:1]):
                write_rows(raw, rows)
                with self.assertRaises(audit.ExpansionAuditError):
                    audit.read_raw(raw, "screening", item, audit.sha256(raw))

    def test_rehashed_summary_tampering_still_fails_raw_reconciliation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan, item, raw, _ = fixture_stage(root)
            diagnostic = audit.read_json(raw.with_suffix(".diagnostics.json"))
            diagnostic["summary"]["wins"] += 1
            save_json(raw.with_suffix(".diagnostics.json"), diagnostic)
            rehash_stage(root, plan, item)
            with self.assertRaisesRegex(audit.ExpansionAuditError, "summary differs"):
                audit.audit_stage(root, plan, "screening", [item], FakeStrictGame)

    def test_consistent_rehashed_wrong_outcome_is_caught_by_strict_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan, item, raw, rows = fixture_stage(root)
            rows[0]["winner"] = str((int(rows[0]["winner"]) + 1) % 3)
            rows[0]["won"] = str(int(rows[0]["winner"] == rows[0]["focal_seat"]))
            write_rows(raw, rows)
            sync_stage(root, plan, item)
            with self.assertRaisesRegex(audit.ExpansionAuditError, "replay disagrees"):
                audit.audit_stage(root, plan, "screening", [item], FakeStrictGame)

    def test_inventory_and_symlink_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan, item, raw, _ = fixture_stage(root)
            stray = raw.parent / "unexpected.txt"
            stray.write_text("extra")
            with self.assertRaisesRegex(audit.ExpansionAuditError, "inventory drift"):
                audit.audit_stage(root, plan, "screening", [item], FakeStrictGame)
            stray.unlink()
            external = root / "outcomes.csv.gz"
            raw.rename(external)
            raw.symlink_to(external)
            with self.assertRaisesRegex(audit.ExpansionAuditError, "linked"):
                audit.audit_stage(root, plan, "screening", [item], FakeStrictGame)

    def test_mixed_roster_cycles_and_focal_identity_are_independent(self):
        names, identities = audit.lineup(10, "honest", "mixed", 8, 0)
        self.assertEqual(names[1:], list(reversed([*audit.POLICIES, "honest"])))
        for rotation in range(10):
            rotated, participants = audit.lineup(10, "honest", "mixed", 8, rotation)
            self.assertEqual(participants[rotation], 0)
            self.assertEqual(rotated[rotation:] + rotated[:rotation], names)
            self.assertEqual(set(participants), set(range(10)))

    def test_seed_namespaces_are_distinct(self):
        seeds = [audit.seed_for(profile, stage, n, field, block) for profile in audit.PROFILES
                 for stage in audit.STAGES for n in audit.PLAYERS for field in audit.FIELDS for block in (0, 1, 999)]
        self.assertEqual(len(seeds), len(set(seeds)))


def fixture_plan(root):
    source_root = root / "live-source"
    source_root.mkdir()
    snapshots = root / "sources"
    snapshots.mkdir()
    sources = {}
    for name in audit.SOURCE_FILES:
        content = (name + " fixture\n").encode("ascii")
        (source_root / name).write_bytes(content)
        (snapshots / name).write_bytes(content)
        sources[name] = hashlib.sha256(content).hexdigest()
    plan = {"schema_version": 1, "profiles": list(audit.PROFILES), "players": list(audit.PLAYERS),
        "policies": list(audit.POLICIES), "fields": list(audit.FIELDS), "opponents": audit.OPPONENTS,
        "mixed_pool": list(audit.POLICIES), "stages": list(audit.STAGES), "seed_rule": audit.SEED_RULE,
        "lineup_rule": audit.LINEUP_RULE, "raw_columns": list(audit.RAW_COLUMNS),
        "max_turns": 1000, "strict_every_action": True, "confirmation_family_size": 135,
        "counter_family_size": 6, "counter_settings": [list(c) for c in audit.COUNTER_SETTINGS],
        "selection_rule": "per profile/player count, rank mean screening win rate equally across five fields; top two; ties lexical policy ID",
        "counter_target_rule": "screening rank first per specified profile/player count",
        "counter_selection_rule": "highest search win rate excluding target; ties lexical policy ID",
        "decision_rng_rule": "engine domain-separated per participant identity, independent from environment/deck randomness",
        "deck_copies": {str(n): 3 if n <= 6 else 4 if n <= 8 else 5 for n in audit.PLAYERS},
        "blocks": {stage: 2 for stage in audit.STAGES}, "configurations": {p: {} for p in audit.POLICIES},
        "inference": {"alpha": 0.05, "practical_threshold": 0.02,
                      "independent_unit": "complete rotation block",
                      "intervals": ["approximate Bonferroni normal", "conservative simultaneous Hoeffding"],
                      "draw_denominator": "all scheduled games", "no_confirmation_retuning": True},
        "preregistration": {"kind": "local hashed source and protocol snapshot",
                            "independent_timestamp_registry": False, "created_utc": "2026-10-18T00:00:00+00:00"},
        "source_sha256": sources}
    save_json(root / "plan.json", plan)
    save_json(root / "preregistration.json", {"plan_sha256": audit.sha256(root / "plan.json"),
        "source_sha256": sources, "created_utc": plan["preregistration"]["created_utc"],
        "kind": "local hashed source and protocol snapshot", "independent_timestamp_registry": False})
    return source_root, plan


class ExpansionAuditPlanTests(unittest.TestCase):
    def test_live_source_and_frozen_snapshots_both_checked(self):
        for destination in ("live-source", "sources"):
            with self.subTest(destination=destination), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source_root, plan = fixture_plan(root)
                self.assertEqual(audit.verify_plan(root, source_root), plan)
                (root / destination / "expansion_simulator.py").write_text("changed")
                with self.assertRaisesRegex(audit.ExpansionAuditError, "source or snapshot changed"):
                    audit.verify_plan(root, source_root)

    def test_snapshot_inventory_and_preregistration_receipt_checked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_root, _ = fixture_plan(root)
            extra = root / "sources" / "extra.py"
            extra.write_text("drift")
            with self.assertRaisesRegex(audit.ExpansionAuditError, "snapshot inventory drift"):
                audit.verify_plan(root, source_root)
            extra.unlink()
            receipt = audit.read_json(root / "preregistration.json")
            receipt["plan_sha256"] = "0" * 64
            save_json(root / "preregistration.json", receipt)
            with self.assertRaisesRegex(audit.ExpansionAuditError, "Preregistration receipt"):
                audit.verify_plan(root, source_root)

    def test_seed_protocol_and_multiplicity_changes_rejected(self):
        for key, changed in (("seed_rule", "different"), ("confirmation_family_size", 1),
                             ("strict_every_action", False), ("max_turns", 99)):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source_root, plan = fixture_plan(root)
                plan[key] = changed
                save_json(root / "plan.json", plan)
                with self.assertRaisesRegex(audit.ExpansionAuditError, "Unsupported frozen protocol"):
                    audit.verify_plan(root, source_root)

    def test_independent_selection_uses_complete_roster_and_lexical_ties(self):
        rows = [{"profile": p, "players": n, "field": f, "candidate": c, "wins": 1}
                for p in audit.PROFILES for n in audit.PLAYERS for f in audit.FIELDS for c in audit.POLICIES]
        selection = audit.select_finalists(rows)
        self.assertTrue(all((r["first"], r["second"]) == ("balanced", "bluff") for r in selection["finalists"]))
        with self.assertRaisesRegex(audit.ExpansionAuditError, "Incomplete screening"):
            audit.select_finalists(rows[:-1])
        search = [{"profile": p, "players": n, "field": "vs_balanced", "candidate": c, "wins": 1}
                  for p, n in audit.COUNTER_SETTINGS for c in audit.POLICIES]
        counters = audit.select_counters(search, selection)
        self.assertTrue(all((r["first"], r["second"]) == ("bluff", "balanced") for r in counters["pairs"]))
        with self.assertRaisesRegex(audit.ExpansionAuditError, "Incomplete counter"):
            audit.select_counters(search[:-1], selection)


if __name__ == "__main__":
    unittest.main()
