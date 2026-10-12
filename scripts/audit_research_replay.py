"""Independently spot-replay every frozen Coup research job.

The execution runner is deliberately not imported. This audit reconstructs
seeds, opponent lineups, participant identities, and physical seats from the
saved plans, then compares fresh strict games with sampled raw CSV rows.
Run after all seven stages to write research_results/2026-10-12-v2/replay-audit.json.
Use ``--stages tuning`` for a read-only partial check while later stages run.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / 'research_results' / '2026-10-12-v2'
STAGES = ('tuning', 'screening', 'confirmation', 'counter_search',
          'counters', 'ablations', 'stress')
RAW_COLUMNS = ('stage', 'players', 'field', 'candidate', 'block', 'rotation',
               'seed', 'winner', 'focal_seat', 'won', 'draw', 'turns')
SEED_FORMULA = '202610120000000 + stage_index*10^12 + n*10^9 + field_index*10^6 + block'
SEED_BASE = 202610120000000
SAFE_NAME = re.compile(r'^[a-z][a-z0-9_]*$')


def sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Missing or linked audit input: {path}')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path):
    sha256(path)
    return json.loads(path.read_text(encoding='utf-8'))


def checked_name(value: str) -> str:
    if not isinstance(value, str) or not SAFE_NAME.fullmatch(value):
        raise ValueError(f'Unsafe policy or field name: {value!r}')
    return value


def verify_global_plan(plan: dict) -> None:
    if plan.get('seed_namespaces') != list(STAGES) or plan.get('seed_formula') != SEED_FORMULA:
        raise ValueError('Unknown seed namespace or formula')
    if plan.get('raw_columns') != list(RAW_COLUMNS):
        raise ValueError('Unknown raw row schema')
    if plan.get('strict_every_action') is not True or plan.get('max_turns') != 1000:
        raise ValueError('Replay requires the frozen strict 1000-turn rules profile')
    source = plan.get('source_sha256')
    if not isinstance(source, dict) or not source or 'research_strategies.py' not in source:
        raise ValueError('Missing frozen execution source digests')
    for name, expected in source.items():
        if not isinstance(name, str) or Path(name).name != name or '/' in name:
            raise ValueError(f'Unsafe source name: {name!r}')
        if sha256(ROOT / name) != expected:
            raise ValueError(f'Frozen research source changed: {name}')
    if not isinstance(plan.get('opponents'), dict) or not isinstance(plan.get('mixed_pool'), list):
        raise ValueError('Missing opponent roster definitions')


def seed_from_plan(plan: dict, stage_plan: dict, stage: str, players: int,
                   field: str, block: int) -> int:
    """Calculate the published seed coordinate without using runner helpers."""
    namespaces = plan['seed_namespaces']
    fields = stage_plan['fields']
    return (SEED_BASE + namespaces.index(stage) * 10**12 + players * 10**9
            + fields.index(field) * 10**6 + block)


def lineup_from_plan(plan: dict, players: int, field: str, candidate: str,
                     block: int, rotation: int) -> tuple[list[str], list[int], int | None]:
    """Build identity-to-seat assignments; identity zero is the focal policy."""
    if not 2 <= players <= 6 or not 0 <= rotation < players:
        raise ValueError('Invalid player count or rotation')
    checked_name(field)
    checked_name(candidate)
    cycle_length = None
    if field in plan['opponents']:
        opponents = [checked_name(plan['opponents'][field])] * (players - 1)
    elif field.startswith('vs_'):
        opponents = [checked_name(field[3:])] * (players - 1)
    elif field == 'selfplay':
        opponents = [candidate] * (players - 1)
    else:
        if field == 'mixed':
            pool = plan['mixed_pool']
        else:
            pools = plan.get('stress_pools')
            if not isinstance(pools, dict) or field not in pools:
                raise ValueError(f'Stress roster absent from frozen plan: {field}')
            pool = pools[field]
        if not isinstance(pool, list) or not pool:
            raise ValueError(f'Empty or invalid opponent pool: {field}')
        pool = [checked_name(item) for item in pool]
        cycle_length = len(pool)
        opponents = [pool[(block + identity - 1) % cycle_length]
                     for identity in range(1, players)]
        if (block // cycle_length) % 2:
            opponents = list(reversed(opponents))

    physical_policies = [''] * players
    physical_identities = [-1] * players
    for identity, policy in enumerate([candidate, *opponents]):
        seat = (identity + rotation) % players
        physical_policies[seat] = policy
        physical_identities[seat] = identity
    if physical_identities[rotation] != 0 or sorted(physical_identities) != list(range(players)):
        raise ValueError('Focal participant identity did not rotate correctly')
    return physical_policies, physical_identities, cycle_length


def sample_blocks(blocks: int, cycle_length: int | None) -> list[int]:
    if blocks < 1:
        raise ValueError('Job has no blocks')
    choices = {0, blocks // 2, blocks - 1}
    # In cyclic fields, explicitly sample the first reversed roster cycle.
    if cycle_length is not None and cycle_length < blocks:
        choices.add(cycle_length)
    return sorted(choices)


def raw_filename(job: dict) -> str:
    return f"{job['players']}-{checked_name(job['field'])}-{checked_name(job['candidate'])}.csv.gz"


def read_raw_job(path: Path, plan: dict, stage_plan: dict, stage: str,
                 job: dict, chosen: set[int], expected_digest: str) -> dict[tuple[int, int], dict]:
    """Independently check all row coordinates, retaining sampled rows only."""
    if sha256(path) != expected_digest:
        raise ValueError(f'Raw file changed after manifest check: {path}')
    players, blocks = job['players'], job['blocks']
    expected_fields = (stage, str(players), job['field'], job['candidate'])
    selected = {}
    seen = set()
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != RAW_COLUMNS:
            raise ValueError(f'Raw schema mismatch: {path}')
        for row in reader:
            if None in row or tuple(row[key] for key in RAW_COLUMNS[:4]) != expected_fields:
                raise ValueError(f'Raw job identity mismatch: {path}')
            block, rotation = int(row['block']), int(row['rotation'])
            key = block, rotation
            if key in seen or not 0 <= block < blocks or not 0 <= rotation < players:
                raise ValueError(f'Duplicate or invalid raw coordinate: {path}: {key}')
            seen.add(key)
            winner = None if row['winner'] == '' else int(row['winner'])
            focal_seat = int(row['focal_seat'])
            seed = seed_from_plan(plan, stage_plan, stage, players, job['field'], block)
            if (int(row['seed']) != seed or focal_seat != rotation or
                winner is not None and not 0 <= winner < players or
                int(row['won']) != int(winner == focal_seat) or
                int(row['draw']) != int(winner is None) or
                not 0 < int(row['turns']) <= plan['max_turns']):
                raise ValueError(f'Invalid raw outcome flags, seat, or seed: {path}: {key}')
            if block in chosen:
                selected[key] = {'seed': seed, 'winner': winner,
                                 'focal_seat': focal_seat, 'turns': int(row['turns'])}
    if len(seen) != blocks * players or len(selected) != len(chosen) * players:
        raise ValueError(f'Incomplete raw job or replay sample: {path}')
    if sha256(path) != expected_digest:
        raise ValueError(f'Raw file changed while it was read: {path}')
    return selected


def verify_stage_manifest(stage_dir: Path, stage: str, plan: dict,
                          global_digest: str, stage_digest: str, games: int) -> tuple[str, dict]:
    manifest_path = stage_dir / 'manifest.json'
    manifest = read_json(manifest_path)
    if (manifest.get('stage') != stage or manifest.get('global_plan_sha256') != global_digest or
        manifest.get('plan_sha256') != stage_digest or
        manifest.get('source_sha256') != plan['source_sha256'] or
        manifest.get('scheduled_games') != games):
        raise ValueError(f'Frozen manifest mismatch: {stage}')
    listed = manifest.get('files')
    if not isinstance(listed, dict):
        raise ValueError(f'Invalid frozen file inventory: {stage}')
    actual = {path.name for path in stage_dir.iterdir() if path.name != 'manifest.json'}
    if actual != set(listed):
        raise ValueError(f'Frozen file inventory drift: {stage}')
    for name, expected in listed.items():
        if Path(name).name != name or sha256(stage_dir / name) != expected:
            raise ValueError(f'Frozen stage file changed: {stage}/{name}')
    return sha256(manifest_path), listed


def audit_stage(output: Path, plan: dict, global_digest: str, stage: str,
                game_class) -> dict:
    stage_dir = output / stage
    stage_plan_path = stage_dir / 'plan.json'
    stage_plan = read_json(stage_plan_path)
    stage_digest = sha256(stage_plan_path)
    jobs = stage_plan.get('jobs')
    fields = stage_plan.get('fields')
    if (stage_plan.get('stage') != stage or stage_plan.get('global_plan_sha256') != global_digest or
        stage_plan.get('source_sha256') != plan['source_sha256'] or
        not isinstance(jobs, list) or not jobs or not isinstance(fields, list) or
        not fields or len(fields) != len(set(fields))):
        raise ValueError(f'Frozen stage plan mismatch: {stage}')
    expected_fields = list(dict.fromkeys(job['field'] for job in jobs))
    if fields != expected_fields:
        raise ValueError(f'Field index schedule mismatch: {stage}')
    names = [raw_filename(job) for job in jobs]
    if len(names) != len(set(names)):
        raise ValueError(f'Duplicate raw jobs in stage plan: {stage}')
    games = sum(job['players'] * job['blocks'] for job in jobs)
    manifest_digest, stage_files = verify_stage_manifest(stage_dir, stage, plan,
                                                         global_digest, stage_digest, games)
    raw_inventory = {path.name for path in stage_dir.glob('*.csv.gz')}
    if raw_inventory != set(names):
        raise ValueError(f'Raw file inventory differs from stage jobs: {stage}')

    replayed = 0
    evidence = hashlib.sha256()
    for job_index, job in enumerate(jobs, 1):
        players, blocks, field, candidate = (job[key] for key in
                                             ('players', 'blocks', 'field', 'candidate'))
        if not 2 <= players <= 6 or blocks < 1 or field not in fields:
            raise ValueError(f'Invalid job coordinates in {stage}: {job}')
        _, _, cycle_length = lineup_from_plan(plan, players, field, candidate, 0, 0)
        chosen = sample_blocks(blocks, cycle_length)
        rows = read_raw_job(stage_dir / raw_filename(job), plan, stage_plan,
                            stage, job, set(chosen), stage_files[raw_filename(job)])
        for block in chosen:
            seed = seed_from_plan(plan, stage_plan, stage, players, field, block)
            for rotation in range(players):
                policies, identities, _ = lineup_from_plan(plan, players, field,
                                                            candidate, block, rotation)
                row = rows[block, rotation]
                if row['seed'] != seed or identities[row['focal_seat']] != 0:
                    raise ValueError(f'Focal identity or seed mismatch: {stage}/{raw_filename(job)}')
                trial = game_class(players, seed, policies,
                                   max_turns=plan['max_turns'], strict=True)
                winner = trial.run()
                trial.validate()
                if winner != row['winner'] or trial.turn != row['turns']:
                    raise ValueError(
                        f'Replay disagreement: {stage}/{raw_filename(job)} '
                        f'block={block} rotation={rotation}; '
                        f'raw=({row["winner"]},{row["turns"]}) '
                        f'replay=({winner},{trial.turn})'
                    )
                winner_identity = None if winner is None else identities[winner]
                evidence.update(json.dumps((stage, players, field, candidate, block,
                                            rotation, seed, winner_identity, trial.turn),
                                           separators=(',', ':')).encode('utf-8') + b'\n')
                replayed += 1
        if job_index % 25 == 0 or job_index == len(jobs):
            print(f'{stage}: replayed {job_index}/{len(jobs)} jobs', flush=True)
    if sha256(stage_plan_path) != stage_digest or sha256(stage_dir / 'manifest.json') != manifest_digest:
        raise ValueError(f'Frozen stage plan or manifest changed during replay: {stage}')
    return {'stage': stage, 'stage_plan_sha256': stage_digest,
            'stage_manifest_sha256': manifest_digest, 'jobs': len(jobs),
            'raw_games': games, 'replayed_games': replayed,
            'replay_identity_outcomes_sha256': evidence.hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--stages', nargs='+', choices=STAGES, default=list(STAGES),
                        help='Read-only partial audit when fewer than all seven stages are chosen')
    args = parser.parse_args()
    if len(args.stages) != len(set(args.stages)):
        raise ValueError('Duplicate selected stages')
    output = args.results_dir.resolve(strict=True)
    global_path = output / 'plan.json'
    plan = read_json(global_path)
    verify_global_plan(plan)
    global_digest = sha256(global_path)

    # Import the tested implementation only after verifying its frozen bytes.
    sys.path.insert(0, str(ROOT))
    from research_strategies import ResearchGame

    selected_stages = [stage for stage in STAGES if stage in args.stages]
    stage_results = [audit_stage(output, plan, global_digest, stage, ResearchGame)
                     for stage in selected_stages]
    verify_global_plan(plan)
    if sha256(global_path) != global_digest:
        raise ValueError('Global plan changed during replay')
    receipt = {'schema_version': 1, 'status': 'passed',
               'sample_rule': 'first, midpoint, last, first reversed cycle; every physical seat',
               'global_plan_sha256': global_digest, 'source_sha256': plan['source_sha256'],
               'audit_source_sha256': sha256(Path(__file__)),
               'stages': stage_results, 'total_jobs': sum(s['jobs'] for s in stage_results),
               'total_raw_games': sum(s['raw_games'] for s in stage_results),
               'total_replayed_games': sum(s['replayed_games'] for s in stage_results)}
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + '\n'
    if set(args.stages) == set(STAGES):
        receipt_path = output / 'replay-audit.json'
        if receipt_path.exists():
            if receipt_path.read_text(encoding='utf-8') != rendered:
                raise ValueError('Existing replay audit differs; preserve it for review')
        else:
            temporary = output / 'replay-audit.json.part'
            temporary.write_text(rendered, encoding='utf-8')
            temporary.replace(receipt_path)
        print(f'All seven stages passed; receipt: {receipt_path}')
    else:
        print(rendered)


if __name__ == '__main__':
    main()
