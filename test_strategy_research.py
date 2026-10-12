"""Independent scheduling, identity, preservation, and resumability checks."""
from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
import tempfile
import unittest

import run_strategy_research as runner
from research_statistics import audit_panel


class ResearchProtocolTests(unittest.TestCase):
    def test_distinct_stage_player_field_block_namespaces(self):
        seeds = [runner.seed_for(stage, n, field, block)
                 for stage in runner.STAGES for n in range(2,7)
                 for field in range(7) for block in (0,31,99,999)]
        self.assertEqual(len(seeds), len(set(seeds)))
        for invalid in [('bogus',4,0,0), ('tuning',7,0,0), ('tuning',4,100,0), ('tuning',4,0,100000)]:
            with self.assertRaises(ValueError): runner.seed_for(*invalid)

    def test_distinct_focal_identity_with_duplicate_policy_names(self):
        for n in range(2,7):
            for seat in range(n):
                names, identities = runner.roster(n, 'baseline', 'honest', 0, seat)
                self.assertEqual(names, ['baseline'] * n)
                self.assertEqual(identities[seat], 0)
                self.assertEqual(set(identities), set(range(n)))

    def test_mixed_duels_cover_all_opponent_types(self):
        opponents = [runner.roster(2, 'baseline', 'mixed', block, 0)[0][1]
                     for block in range(14)]
        self.assertEqual(set(opponents), set(runner.MIXED))
        self.assertTrue(all(opponents.count(name) == 2 for name in runner.MIXED))

    def test_rotations_preserve_lineup_circular_order(self):
        for n in range(2,7):
            for block in (0,7,14):
                initial, _ = runner.roster(n, 'baseline', 'mixed', block, 0)
                for seat in range(n):
                    names, _ = runner.roster(n, 'baseline', 'mixed', block, seat)
                    self.assertEqual(names[seat:] + names[:seat], initial)

    def test_freeze_rejects_source_or_schedule_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'plan.json'
            runner.freeze(path, {'source': 'original', 'blocks': 20})
            runner.freeze(path, {'source': 'original', 'blocks': 20})
            with self.assertRaises(ValueError): runner.freeze(path, {'source': 'changed', 'blocks': 20})
            self.assertEqual(json.loads(path.read_text())['source'], 'original')
            arrays = Path(tmp) / 'arrays.json'
            runner.freeze(arrays, {'lineup': ('a','b')})
            runner.freeze(arrays, {'lineup': ['a','b']})

    def test_raw_identity_complete_blocks_replay_and_deterministic_gzip(self):
        job = {'players': 2, 'field': 'honest', 'candidate': 'baseline', 'blocks': 3}
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first = runner.run_job('tuning', job, 0, a)
            second = runner.run_job('tuning', job, 0, b)
            path = Path(a) / runner.filename(job)
            self.assertEqual(path.read_bytes(), (Path(b) / path.name).read_bytes())
            with gzip.open(path, 'rt', newline='') as file: rows = list(csv.DictReader(file))
            panel = audit_panel(rows, 2, 'honest', ['baseline'], 3, stage='tuning')
            self.assertEqual(panel['wins']['baseline'], first['summary']['wins'])
            for row in rows:
                n, seat, block = (int(row[key]) for key in ('players','rotation','block'))
                names, ids = runner.roster(n, row['candidate'], row['field'], block, seat)
                game = runner.ResearchGame(n, int(row['seed']), names, strict=True)
                winner = game.run()
                self.assertEqual('' if winner is None else str(winner), row['winner'])
                self.assertEqual(int(row['turns']), game.turn)
                self.assertEqual(ids[int(row['focal_seat'])], 0)
            self.assertEqual(first, second)
            self.assertEqual(first, runner.run_job('tuning', job, 0, a))
            diagnostic = path.with_suffix('.diagnostics.json')
            tampered = json.loads(diagnostic.read_text())
            tampered['summary']['wins'] = 999
            runner.save_json(diagnostic, tampered)
            with self.assertRaisesRegex(ValueError, 'summary differs'): runner.run_job('tuning', job, 0, a)
            runner.save_json(diagnostic, first)
            path.write_bytes(b'tampered')
            with self.assertRaises(ValueError): runner.run_job('tuning', job, 0, a)

    def test_selection_fixed_before_confirmation(self):
        rows = [{'players':n, 'field':f, 'candidate':c, 'win_rate':rate}
                for n in range(2,7) for f in runner.FIELDS
                for c,rate in [('z',.3),('a',.3),('loser',.1)]]
        pairs = runner.select_pairs(rows)
        self.assertEqual(len(pairs), 35)
        self.assertTrue(all(p['first'] == 'a' and p['second'] == 'z' for p in pairs))
        self.assertEqual(runner.rank_global(rows), ['a','z','loser'])


if __name__ == '__main__': unittest.main()
