"""Frozen, separate tuning/selection/confirmation panels for finite Coup policies."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
import gzip
import hashlib
import io
import json
import platform
from pathlib import Path

from research_strategies import ResearchGame, configurations

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'research_results' / '2026-10-12-v2'
CONTROLS = ('baseline', 'income', 'foreign_aid', 'taxer', 'captain', 'assassin',
            'exchange', 'bluff_heavy', 'challenge_low', 'challenge_heavy', 'block_aggressive')
ADVANCED = ('card_cautious', 'card_balanced', 'card_bold', 'public_learning',
            'eliminator', 'defensive', 'exchange_builder')
FIELDS = ('honest', 'bluffing', 'skeptical', 'rational', 'learning', 'random', 'mixed')
OPPONENTS = dict(zip(FIELDS[:-1], ('baseline', 'bluff_heavy', 'challenge_heavy',
                                 'card_balanced', 'public_learning', 'public_random')))
MIXED = ('baseline', 'bluff_heavy', 'challenge_heavy', 'card_balanced',
         'public_learning', 'public_random', 'eliminator')
STAGES = ('tuning', 'screening', 'confirmation', 'counter_search', 'counters', 'ablations', 'stress')
ABLATIONS = ('ablate_no_claim_cards', 'ablate_no_history', 'ablate_random_target', 'ablate_fixed_retention')
STRESS_FIELDS = ('selfplay', 'assault', 'economy', 'chaos', 'alternating', 'mixed')
STRESS_POOLS = {'assault': ('eliminator', 'assassin', 'bluff_heavy'),
                'economy': ('taxer', 'captain', 'exchange_builder'),
                'chaos': ('public_random', 'block_aggressive', 'challenge_heavy'),
                'alternating': ('card_cautious', 'card_bold', 'public_learning')}
RAW = ('stage', 'players', 'field', 'candidate', 'block', 'rotation', 'seed',
       'winner', 'focal_seat', 'won', 'draw', 'turns')
SUMMARY = ('stage', 'players', 'field', 'candidate', 'games', 'wins', 'draws',
           'win_rate', 'mean_turns', 'blocks')
SOURCE_FILES = ('coup_simulator.py', 'research_strategies.py', 'run_strategy_research.py',
                'research_statistics.py', 'analyze_strategy_research.py',
                'test_extensive_rules.py', 'test_research_strategies.py',
                'test_research_statistics.py', 'test_strategy_research.py', 'test_analyze_strategy_research.py')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def freeze(path, value):
    """A completed or interrupted panel can resume only its exact frozen plan."""
    value = json.loads(json.dumps(value))  # JSON arrays normalize tuple/list representation.
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError(f'Frozen plan mismatch: {path}; use a new study directory')
    else:
        save_json(path, value)


def source_hashes():
    return {name: digest(ROOT / name) for name in SOURCE_FILES}


def seed_for(stage, n, field_index, block):
    if stage not in STAGES or not 2 <= n <= 6 or not 0 <= field_index < 100 or not 0 <= block < 100000:
        raise ValueError('Invalid seed coordinate')
    return 202610120000000 + STAGES.index(stage) * 1000000000000 + n * 1000000000 + field_index * 1000000 + block


def roster(n, candidate, field, block, rotation):
    """Rotate distinct identity 0, even when all policy names are identical."""
    if not 2 <= n <= 6 or not 0 <= rotation < n:
        raise ValueError('Invalid rotation')
    if field in OPPONENTS:
        opponents = [OPPONENTS[field]] * (n - 1)
    elif field.startswith('vs_'):
        opponents = [field[3:]] * (n - 1)
    elif field == 'selfplay':
        opponents = [candidate] * (n - 1)
    else:
        pools = {'mixed': MIXED, **STRESS_POOLS}
        if field not in pools:
            raise ValueError('Unknown field')
        pool = pools[field]
        opponents = [pool[(block + j) % len(pool)] for j in range(n - 1)]
        if (block // len(pool)) % 2:
            opponents.reverse()
    names = [candidate] + opponents
    identities = list(range(n))
    if rotation:
        names = names[-rotation:] + names[:-rotation]
        identities = identities[-rotation:] + identities[:-rotation]
    if identities[rotation] != 0:
        raise ValueError('Focal identity attribution failed')
    return names, identities


def filename(job):
    return f"{job['players']}-{job['field']}-{job['candidate']}.csv.gz"


def validate_cached(cached, path, stage, job, field_index):
    n, blocks = job['players'], job['blocks']
    wins = draws = turns = 0
    seen = set()
    with gzip.open(path, 'rt', newline='') as file:
        reader = csv.DictReader(file)
        if tuple(reader.fieldnames) != RAW: raise ValueError('Cached raw schema differs')
        for row in reader:
            block, rotation = int(row['block']), int(row['rotation'])
            winner = None if row['winner'] == '' else int(row['winner'])
            key = block, rotation
            if (key in seen or not 0 <= block < blocks or not 0 <= rotation < n or
                row['stage'] != stage or int(row['players']) != n or row['field'] != job['field'] or
                row['candidate'] != job['candidate'] or int(row['focal_seat']) != rotation or
                int(row['seed']) != seed_for(stage, n, field_index, block) or
                (winner is not None and not 0 <= winner < n) or
                int(row['won']) != int(winner == rotation) or int(row['draw']) != int(winner is None) or
                not 0 < int(row['turns']) <= 1000):
                raise ValueError('Cached raw job differs from planned panel')
            seen.add(key); wins += int(row['won']); draws += int(row['draw']); turns += int(row['turns'])
    expected = {'stage': stage, 'players': n, 'field': job['field'], 'candidate': job['candidate'],
                'games': n * blocks, 'wins': wins, 'draws': draws, 'win_rate': wins / (n * blocks),
                'mean_turns': turns / (n * blocks), 'blocks': blocks}
    if len(seen) != n * blocks or cached['summary'] != expected:
        raise ValueError('Cached summary differs from raw games')


def run_job(stage, job, field_index, directory, expected_sources=None):
    if expected_sources is not None and source_hashes() != expected_sources:
        raise ValueError('Research source changed before job')
    n, field, candidate, blocks = (job[key] for key in ('players', 'field', 'candidate', 'blocks'))
    path = Path(directory) / filename(job)
    diagnostic = path.with_suffix('.diagnostics.json')
    if path.exists():
        if not diagnostic.exists():
            raise ValueError('Partial raw job lacks diagnostics; inspect before resuming')
        cached = json.loads(diagnostic.read_text())
        if cached['raw_sha256'] != digest(path) or cached['job'] != job or cached['stage'] != stage:
            raise ValueError('Cached job differs from frozen execution')
        validate_cached(cached, path, stage, job, field_index)
        if expected_sources is not None and source_hashes() != expected_sources:
            raise ValueError('Research source changed during cached job audit')
        return cached
    wins = draws = turns = 0
    actions, events, seats = Counter(), Counter(), {str(i): {'wins': 0, 'draws': 0, 'games': 0} for i in range(n)}
    focal_actions, focal_events, focal_roles = Counter(), Counter(), Counter()
    temporary = path.with_suffix('.part')
    with temporary.open('wb') as raw_file:
        with gzip.GzipFile(filename='', fileobj=raw_file, mode='wb', mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding='utf-8', newline='') as text_file:
                writer = csv.DictWriter(text_file, fieldnames=RAW)
                writer.writeheader()
                for block in range(blocks):
                    seed = seed_for(stage, n, field_index, block)
                    for rotation in range(n):
                        names, identities = roster(n, candidate, field, block, rotation)
                        # Strict conservation/influence/coin checks run after every action.
                        trial = ResearchGame(n, seed, names, max_turns=1000, strict=True)
                        winner = trial.run()
                        won, draw = winner == rotation, winner is None
                        if identities[rotation] != 0:
                            raise ValueError('Focal seat is not focal identity')
                        wins += won; draws += draw; turns += trial.turn
                        seats[str(rotation)]['wins'] += int(won)
                        seats[str(rotation)]['draws'] += int(draw)
                        seats[str(rotation)]['games'] += 1
                        actions.update(trial.action_counts)
                        events.update(event[0] for event in trial.events)
                        for event in trial.events:
                            if len(event) > 1 and event[1] == rotation:
                                focal_events[event[0]] += 1
                                if event[0] == 'action': focal_actions[event[2]] += 1
                                if event[0] in ('proved','disproved','lose'): focal_roles[event[0] + ':' + event[2]] += 1
                        writer.writerow(dict(zip(RAW, (stage, n, field, candidate, block, rotation,
                            seed, '' if draw else winner, rotation, int(won), int(draw), trial.turn))))
    if expected_sources is not None and source_hashes() != expected_sources:
        raise ValueError('Research source changed during job; do not accept partial output')
    temporary.replace(path)
    result = {'stage': stage, 'job': job, 'raw_sha256': digest(path), 'summary': {
        'stage': stage, 'players': n, 'field': field, 'candidate': candidate,
        'games': n * blocks, 'wins': wins, 'draws': draws,
        'win_rate': wins / (n * blocks), 'mean_turns': turns / (n * blocks), 'blocks': blocks},
        'actions': dict(actions), 'events': dict(events), 'seats': seats,
        'focal_actions': dict(focal_actions), 'focal_events': dict(focal_events), 'focal_roles': dict(focal_roles)}
    save_json(diagnostic, result)
    return result


def make_jobs(candidates, players, fields, blocks):
    return [{'players': n, 'field': field, 'candidate': name, 'blocks': blocks}
            for n in players for field in fields for name in candidates]


def run_stage(output, global_plan, stage, jobs, workers, pairs=None, extra=None):
    if source_hashes() != global_plan['source_sha256']:
        raise ValueError('Execution source changed after global freeze')
    directory = output / stage
    directory.mkdir(exist_ok=True)
    fields = list(dict.fromkeys(job['field'] for job in jobs))
    plan = {'stage': stage, 'jobs': jobs, 'fields': fields, 'pairs': pairs or [],
            'global_plan_sha256': digest(output / 'plan.json'),
            'source_sha256': global_plan['source_sha256'], 'extra': extra or {}}
    freeze(directory / 'plan.json', plan)
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_job, stage, job, fields.index(job['field']), directory, global_plan['source_sha256']) for job in jobs]
        for number, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if number % 25 == 0 or number == len(jobs):
                print(f'{stage}: {number}/{len(jobs)} jobs complete', flush=True)
    if source_hashes() != global_plan['source_sha256']:
        raise ValueError('Research source changed during stage')
    results.sort(key=lambda r: (r['summary']['players'], r['summary']['field'], r['summary']['candidate']))
    with (directory / 'summaries.csv').open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=SUMMARY)
        writer.writeheader(); writer.writerows(result['summary'] for result in results)
    diagnostics = {'actions': dict(sum((Counter(r['actions']) for r in results), Counter())),
                   'events': dict(sum((Counter(r['events']) for r in results), Counter())),
                   'games': sum(r['summary']['games'] for r in results),
                   'draws': sum(r['summary']['draws'] for r in results),
                   'seats': {filename(r['job']): r['seats'] for r in results}}
    save_json(directory / 'diagnostics.json', diagnostics)
    files = {path.name: digest(path) for path in sorted(directory.iterdir())
             if path.name != 'manifest.json' and path.is_file() and not path.name.endswith('.part')}
    save_json(directory / 'manifest.json', {'stage': stage, 'files': files,
        'plan_sha256': digest(directory / 'plan.json'), 'global_plan_sha256': digest(output / 'plan.json'),
        'source_sha256': global_plan['source_sha256'],
        'scheduled_games': diagnostics['games']})
    return [r['summary'] for r in results]


def rank_global(rows):
    names = sorted({row['candidate'] for row in rows})
    # Equal weights across cells, scaled by symmetric player-count reference.
    score = {name: sum(row['players'] * row['win_rate'] for row in rows if row['candidate'] == name)
             / sum(row['candidate'] == name for row in rows) for name in names}
    return sorted(names, key=lambda name: (-score[name], name))


def select_pairs(rows):
    cells = sorted({(row['players'], row['field']) for row in rows})
    pairs = []
    for n, field in cells:
        ranked = sorted((r for r in rows if r['players'] == n and r['field'] == field),
                        key=lambda r: (-r['win_rate'], r['candidate']))
        pairs.append({'players': n, 'field': field, 'first': ranked[0]['candidate'], 'second': ranked[1]['candidate']})
    return pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--freeze-only', action='store_true', help='save the protocol before generating any outcomes')
    parser.add_argument('--stop-after', choices=STAGES)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        raise ValueError('Use 1–8 workers')
    output = args.output_dir.resolve()
    if output.is_relative_to(ROOT) and not any(output.is_relative_to(ROOT / name) for name in ('research_results','.ai-work')):
        raise ValueError('Cannot write over the original study')
    output.mkdir(parents=True, exist_ok=True)
    plan = {'date': '2026-10-12', 'rules_profile': 'standard base Coup; 2-player first seat one coin',
        'python': platform.python_version(), 'source_sha256': source_hashes(),
        'configurations': configurations(), 'controls': list(CONTROLS), 'fields': list(FIELDS),
        'opponents': OPPONENTS, 'mixed_pool': list(MIXED), 'stress_pools': STRESS_POOLS, 'strict_every_action': True,
        'max_turns': 1000, 'raw_columns': list(RAW), 'seed_namespaces': list(STAGES),
        'seed_formula': '202610120000000 + stage_index*10^12 + n*10^9 + field_index*10^6 + block',
        'lineup_rule': 'candidate identity 0; homogeneous opponents, mixed cyclic block+j with alternate cycle reversal; rotate all identities right by focal rotation',
        'rng_rule': 'environment seed; SHA-256 domain-separated decision_seed(seed,physical_seat) in research_strategies.py; legacy controls also separated',
        'schedule': {'tuning': {'blocks': 32, 'players': [2,4,6], 'candidates': 24},
            'screening': {'blocks': 100, 'players': [2,3,4,5,6], 'selection': 'six globally ranked tuners + seven advanced + eleven controls'},
            'confirmation': {'blocks': 1000, 'players': [2,3,4,5,6], 'selection': 'union screening top two in each of 35 cells plus baseline/card_balanced/public_learning; no union cap', 'family_size': 35},
            'counter_search': {'blocks': 32, 'players': [2,4], 'selection': 'global screening leader + highest global advanced distinct from leader; all screening candidates'},
            'counters': {'blocks': 1000, 'players': [2,4], 'selection': 'best non-target counter per target/count in D search; paired against target selfplay control', 'family_size': 4},
            'ablations': {'blocks': 500, 'players': [2,4], 'components': list(ABLATIONS), 'family_size': 56},
            'stress': {'blocks': 100, 'players': [6], 'fields': list(STRESS_FIELDS), 'candidates': list(ADVANCED) + ['baseline','bluff_heavy','challenge_heavy']}},
        'inference': {'alpha': 0.05, 'practical_difference': 0.02, 'unit': 'complete seed rotation block',
                      'intervals': ['approximate Bonferroni normal', 'conservative Hoeffding simultaneous']},
        'selection_tiebreak': 'lexical candidate ID after descending observed win_rate; global score equals mean n*win_rate across all cells'}
    freeze(output / 'plan.json', plan)
    if args.freeze_only:
        print(f'Frozen protocol without outcomes: {output / "plan.json"}', flush=True)
        return
    tuning = run_stage(output, plan, 'tuning', make_jobs([f'search_{i:02d}' for i in range(24)], [2,4,6], FIELDS, 32), args.workers)
    if args.stop_after == 'tuning': return
    candidates = sorted(set(rank_global(tuning)[:6]) | set(ADVANCED) | set(CONTROLS))
    screening = run_stage(output, plan, 'screening', make_jobs(candidates, range(2,7), FIELDS, 100), args.workers,
                          extra={'tuners_selected': rank_global(tuning)[:6]})
    if args.stop_after == 'screening': return
    pairs = select_pairs(screening)
    finalists = sorted({p[key] for p in pairs for key in ('first','second')} | {'baseline','card_balanced','public_learning'})
    ranking = rank_global(screening)
    targets = [ranking[0], next(name for name in ranking if name in ADVANCED and name != ranking[0])]
    # Both confirmation contenders and counter targets freeze before C outcomes.
    freeze(output / 'selection.json', {'confirmation_pairs': pairs, 'finalists': finalists,
                                      'counter_targets': targets, 'screening_global_rank': ranking})
    run_stage(output, plan, 'confirmation', make_jobs(finalists, range(2,7), FIELDS, 1000), args.workers, pairs)
    if args.stop_after == 'confirmation': return
    counter_fields = ['vs_' + target for target in targets]
    search = run_stage(output, plan, 'counter_search', make_jobs(candidates, [2,4], counter_fields, 32), args.workers,
                       extra={'targets': targets})
    counter_pairs, jobs = [], []
    for n in (2,4):
        for target, field in zip(targets, counter_fields):
            contenders = sorted((r for r in search if r['players'] == n and r['field'] == field and r['candidate'] != target),
                                key=lambda r: (-r['win_rate'], r['candidate']))
            counter = contenders[0]['candidate']
            counter_pairs.append({'players': n, 'field': field, 'first': counter, 'second': target})
            jobs += make_jobs([counter, target], [n], [field], 1000)
    freeze(output / 'counter_selection.json', {'pairs': counter_pairs})
    if args.stop_after == 'counter_search': return
    run_stage(output, plan, 'counters', jobs, args.workers, counter_pairs, {'targets': targets})
    if args.stop_after == 'counters': return
    ablation_pairs = [{'players': n, 'field': field, 'first': 'public_learning', 'second': name}
                      for n in (2,4) for field in FIELDS for name in ABLATIONS]
    run_stage(output, plan, 'ablations', make_jobs(['public_learning'] + list(ABLATIONS), [2,4], FIELDS, 500), args.workers, ablation_pairs)
    if args.stop_after == 'ablations': return
    run_stage(output, plan, 'stress', make_jobs(list(ADVANCED) + ['baseline','bluff_heavy','challenge_heavy'], [6], STRESS_FIELDS, 100), args.workers)
    print('All frozen panels complete; run independent analysis.', flush=True)


if __name__ == '__main__':
    main()
