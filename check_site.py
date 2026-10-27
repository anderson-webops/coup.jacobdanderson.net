"""Validate the exact static publication and its reproducible study evidence."""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import importlib.util
import json
import math
import re
import tarfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESEARCH_STAGES = ("tuning", "screening", "confirmation", "counter_search",
                   "counters", "ablations", "stress")
RESEARCH_FIELDS = ("honest", "bluffing", "skeptical", "rational",
                   "learning", "random", "mixed")
RESEARCH_ABLATIONS = ("ablate_no_claim_cards", "ablate_no_history",
                      "ablate_random_target", "ablate_fixed_retention")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


class StudyData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_study = False
        self.data = []
        self.csp = None
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script":
            self.scripts.append(attributes)
            self.in_study = attributes.get("id") == "study-data"
        if tag == "meta" and attributes.get("http-equiv") == "Content-Security-Policy":
            self.csp = attributes.get("content")
        require(not any(key.lower().startswith("on") for key in attributes), "Inline event handler")
        require(tag not in ("iframe", "object", "embed", "form"), "Unexpected active content")

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_study = False

    def handle_data(self, data):
        if self.in_study:
            self.data.append(data)


def verify_panel(evidence, prefix):
    manifest = json.loads((evidence / f"{prefix}-manifest.json").read_text())
    names = {"results.csv": f"{prefix}-results.csv", "benchmark_results.csv": f"{prefix}-seats.csv",
             "games.csv": f"{prefix}-games.csv"}
    for name, expected in manifest["checksums_sha256"].items():
        path = evidence / names.get(name, name)
        require(digest(path) == expected, f"Frozen {prefix} evidence changed: {name}")
    summary = rows(evidence / f"{prefix}-results.csv")
    raw = rows(evidence / f"{prefix}-games.csv")
    counts = {}
    for row in raw:
        key = (row["players"], row["field"], row["policy"])
        total, wins, draws = counts.get(key, (0, 0, 0))
        counts[key] = (total + 1, wins + int(row["won"]), draws + int(row["draw"]))
    require(len(counts) == len(summary), f"{prefix} raw summary groups mismatch")
    for row in summary:
        key = (row["players"], row["field"], row["policy"])
        require(counts[key] == tuple(int(row[k]) for k in ("games", "wins", "draws")),
                f"{prefix} raw counts mismatch: {key}")
        require(abs(float(row["win_rate"]) - int(row["wins"]) / int(row["games"])) <= 0.000000500001,
                f"{prefix} rate mismatch: {key}")
    return summary


def verify_research_findings(findings, confirmation_summary):
    """Check the figures used by the new page against its frozen summary."""
    require(isinstance(findings, dict), 'Expanded findings must be an object')
    stages = findings['stages']
    require(isinstance(stages, dict) and set(stages) == set(RESEARCH_STAGES),
            'Expanded stages differ')
    require(sum(stage['games'] for stage in stages.values()) == findings['total_games'],
            'Expanded game total differs')
    reported = findings['confirmation_rows']
    require(isinstance(reported, list) and reported, 'Expanded confirmation rows missing')
    by_key = {}
    cell_candidates = {}
    for row in reported:
        n, field, candidate = row['players'], row['field'], row['candidate']
        key = (n, field, candidate)
        require(n in range(2, 7) and field in RESEARCH_FIELDS and
                isinstance(candidate, str) and candidate and key not in by_key,
                'Expanded confirmation identity differs')
        games, wins, draws = row['games'], row['wins'], row['draws']
        require(games == n * 1000 and 0 <= wins <= games and 0 <= draws <= games - wins and
                math.isfinite(row['win_rate']) and
                abs(row['win_rate'] - wins / games) < 1e-12 and
                math.isfinite(row['mean_turns']) and row['mean_turns'] >= 1,
                'Expanded confirmation rate differs')
        by_key[key] = row
        cell_candidates.setdefault((n, field), set()).add(candidate)
    cells = {(n, field) for n in range(2, 7) for field in RESEARCH_FIELDS}
    require(set(cell_candidates) == cells, 'Expanded confirmation cells differ')
    union = next(iter(cell_candidates.values()))
    require(len(union) >= 3 and all(names == union for names in cell_candidates.values()),
            'Expanded finalist union differs by cell')
    require(len(reported) == 35 * len(union), 'Expanded confirmation row count differs')
    require(stages['confirmation']['games'] == sum(row['games'] for row in reported),
            'Expanded confirmation stage total differs')
    csv_by_key = {}
    for row in confirmation_summary:
        key = (int(row['players']), row['field'], row['candidate'])
        require(key not in csv_by_key, 'Duplicate expanded confirmation CSV row')
        csv_by_key[key] = row
    require(set(csv_by_key) == set(by_key), 'Expanded confirmation CSV identity differs')
    for key, row in by_key.items():
        csv_row = csv_by_key[key]
        require(all(int(csv_row[name]) == row[name] for name in ('games', 'wins', 'draws', 'blocks')) and
                abs(float(csv_row['win_rate']) - row['win_rate']) < 1e-12 and
                abs(float(csv_row['mean_turns']) - row['mean_turns']) < 1e-9,
                'Expanded confirmation CSV value differs')
    pairs = findings['confirmation_pairs']
    require(isinstance(pairs, list) and len(pairs) == 35 and
            {(p['players'], p['field']) for p in pairs} == cells,
            'Expanded preselected comparison family differs')
    for pair in pairs:
        n, field = pair['players'], pair['field']
        first, second = by_key[(n, field, pair['first'])], by_key[(n, field, pair['second'])]
        require(pair['first'] != pair['second'] and
                pair['games_per_candidate'] == n * 1000 and
                pair['first_wins'] == first['wins'] and pair['second_wins'] == second['wins'] and
                abs(pair['first_rate'] - first['win_rate']) < 1e-12 and
                abs(pair['second_rate'] - second['win_rate']) < 1e-12 and
                abs(pair['difference'] - (first['win_rate'] - second['win_rate'])) < 1e-12 and
                pair['normal_family_lower'] <= pair['difference'] <= pair['normal_family_upper'] and
                pair['conservative_family_lower'] <= pair['difference'] <= pair['conservative_family_upper'],
                'Expanded paired comparison differs from confirmation')
        ordered = sorted((by_key[(n, field, name)] for name in union),
                         key=lambda row: (-row['win_rate'], row['candidate']))
        require(pair['observed_leader'] == ordered[0]['candidate'] and
                abs(pair['observed_leader_rate'] - ordered[0]['win_rate']) < 1e-12 and
                pair['observed_leader_is_preselected'] ==
                (ordered[0]['candidate'] in (pair['first'], pair['second'])),
                'Expanded observed leader label differs')
    counters = findings['counters']
    require(isinstance(counters, list) and len(counters) == 4 and
            len({(p['players'], p['field']) for p in counters}) == 4 and
            {p['players'] for p in counters} == {2, 4} and
            len({p['field'] for p in counters}) == 2 and
            all(p['field'] == 'vs_' + p['second'] and
                p['games_per_candidate'] == p['players'] * 1000 and
                p['first'] != p['second'] for p in counters),
            'Expanded counter family differs')
    ablations = findings['ablations']
    expected_ablations = {(n, field, name) for n in (2, 4)
                          for field in RESEARCH_FIELDS for name in RESEARCH_ABLATIONS}
    require(isinstance(ablations, list) and len(ablations) == 56 and
            {(p['players'], p['field'], p['second']) for p in ablations} == expected_ablations and
            all(p['first'] == 'public_learning' and
                p['games_per_candidate'] == p['players'] * 500 for p in ablations),
            'Expanded ablation family differs')
    robustness = findings['equal_field_robustness']
    require(isinstance(robustness, list) and len(robustness) == 5 * len(union) and
            {(r['players'], r['candidate']) for r in robustness} ==
            {(n, candidate) for n in range(2, 7) for candidate in union},
            'Expanded equal-field summary differs')
    for row in robustness:
        values = [by_key[(row['players'], field, row['candidate'])]['win_rate']
                  for field in RESEARCH_FIELDS]
        require(abs(row['equal_field_mean'] - sum(values) / 7) < 1e-12 and
                abs(row['worst_rate'] - min(values)) < 1e-12 and
                row['worst_field'] in RESEARCH_FIELDS and
                abs(by_key[(row['players'], row['worst_field'], row['candidate'])]['win_rate'] -
                    row['worst_rate']) < 1e-12,
                'Expanded robustness rates differ')


def verify_research_bundle(root, evidence, embedded, anchor, publication):
    """Read frozen bundle without extracting paths or running its code."""
    inventory = json.loads((evidence / 'research-bundle-manifest.json').read_text())
    require(0 < len(inventory) < 10000, 'Invalid research bundle inventory')
    saved = {}
    total = 0
    with tarfile.open(evidence / 'research-evidence.tar.gz', 'r:gz') as archive:
        for member in archive:
            name = member.name
            require(member.isfile() and not name.startswith('/') and '..' not in Path(name).parts
                    and '\\' not in name and name in inventory and name not in saved,
                    'Unsafe or unplanned research member')
            total += member.size
            require(total <= 128 * 1024 * 1024, 'Research bundle exceeds bound')
            require(member.size == inventory[name]['size'], 'Research member size mismatch')
            data = archive.extractfile(member).read()
            require(hashlib.sha256(data).hexdigest() == inventory[name]['sha256'], 'Research member digest mismatch')
            saved[name] = data
    require(set(saved) == set(inventory), 'Research bundle member inventory differs')
    prefix = 'research_results/2026-10-12-v2/'
    plan = json.loads(saved[prefix + 'plan.json'])
    require(plan['seed_namespaces'] == list(RESEARCH_STAGES), 'Expanded stage order differs')
    require(plan['source_sha256'] == anchor['expanded_research_source_sha256'], 'Expanded research source differs')
    require(embedded['research_configs'] == plan['configurations'], 'Displayed strategy settings differ')
    for name, expected_hash in plan['source_sha256'].items():
        require(hashlib.sha256(saved[name]).hexdigest() == expected_hash, 'Bundled research source differs')
    findings = json.loads(saved[prefix + 'findings.json'])
    confirmation_summary = list(csv.DictReader(io.StringIO(
        saved[prefix + 'confirmation/summaries.csv'].decode('utf-8'))))
    verify_research_findings(findings, confirmation_summary)
    require(findings == embedded['research'], 'Expanded embedded findings differ')
    require(findings == json.loads((evidence / 'research-findings.json').read_text()), 'Expanded findings download differs')
    require(publication['expanded_study_games'] == findings['total_games'], 'Expanded total differs')
    require(publication['expanded_confirmation_games'] == findings['stages']['confirmation']['games'],
            'Expanded confirmation total differs')
    expected_members = {prefix + name for name in
                        ('plan.json', 'selection.json', 'counter_selection.json',
                         'findings.json', 'FINDINGS.md', 'replay-audit.json')}
    expected_members.update(plan['source_sha256'])
    expected_members.update(('docs/STRATEGY_REVIEW.md', 'docs/RESEARCH_DESIGN.md',
                             'docs/RULES_TEST_REVIEW.md', 'docs/REPLAY_AUDIT.md',
                             'docs/STRATEGY_FINDINGS.md',
                             'scripts/audit_research_replay.py'))
    receipt = json.loads(saved[prefix + 'replay-audit.json'])
    require(receipt['status'] == 'passed' and receipt['schema_version'] == 1 and
            receipt['global_plan_sha256'] == hashlib.sha256(saved[prefix + 'plan.json']).hexdigest() and
            receipt['source_sha256'] == plan['source_sha256'] and
            receipt['audit_source_sha256'] == hashlib.sha256(saved['scripts/audit_research_replay.py']).hexdigest() and
            receipt['total_raw_games'] == findings['total_games'] and
            [entry['stage'] for entry in receipt['stages']] == list(RESEARCH_STAGES),
            'Expanded replay receipt differs')
    stage_games = 0
    for stage in plan['seed_namespaces']:
        stage_prefix = prefix + stage + '/'
        manifest = json.loads(saved[stage_prefix + 'manifest.json'])
        expected_members.add(stage_prefix + 'manifest.json')
        expected_members.update(stage_prefix + name for name in manifest['files'])
        require(manifest['global_plan_sha256'] == hashlib.sha256(saved[prefix + 'plan.json']).hexdigest(), 'Global freeze differs')
        require(manifest['source_sha256'] == plan['source_sha256'], 'Stage research source differs')
        stage_plan = json.loads(saved[stage_prefix + 'plan.json'])
        require(manifest['plan_sha256'] == hashlib.sha256(saved[stage_prefix + 'plan.json']).hexdigest(), 'Stage freeze differs')
        stage_receipt = next(entry for entry in receipt['stages'] if entry['stage'] == stage)
        require(stage_receipt['stage_plan_sha256'] == manifest['plan_sha256'] and
                stage_receipt['stage_manifest_sha256'] == hashlib.sha256(saved[stage_prefix + 'manifest.json']).hexdigest() and
                stage_receipt['jobs'] == len(stage_plan['jobs']),
                'Expanded replay stage differs')
        for name, expected_hash in manifest['files'].items():
            require(hashlib.sha256(saved[stage_prefix + name]).hexdigest() == expected_hash, 'Frozen stage output differs')
        scheduled = sum(job['players'] * job['blocks'] for job in stage_plan['jobs'])
        require(scheduled == manifest['scheduled_games'] == findings['stages'][stage]['games'], 'Stage scheduled total differs')
        require(stage_receipt['raw_games'] == scheduled and stage_receipt['replayed_games'] > 0,
                'Expanded replay counts differ')
        stage_games += scheduled
    require(stage_games == findings['total_games'], 'Research game totals differ')
    require(receipt['total_jobs'] == sum(entry['jobs'] for entry in receipt['stages']) and
            receipt['total_replayed_games'] == sum(entry['replayed_games'] for entry in receipt['stages']) and
            receipt['total_replayed_games'] > 0,
            'Expanded replay totals differ')
    require(set(saved) == expected_members, 'Expanded research member inventory differs')
    require(saved[prefix + 'confirmation/summaries.csv'] == (evidence / 'research-confirmation.csv').read_bytes(), 'Confirmation download differs')
    require(saved[prefix + 'replay-audit.json'] == (evidence / 'research-replay-audit.json').read_bytes(), 'Replay receipt download differs')
    require(saved['research_strategies.py'] == (evidence / 'research_strategies.py').read_bytes(), 'Strategy download differs')
    for bundled, public in [('docs/RESEARCH_DESIGN.md','research-design.md'), ('docs/STRATEGY_REVIEW.md','strategy-review.md'),
                            ('docs/RULES_TEST_REVIEW.md','rules-test-review.md'),
                            ('docs/REPLAY_AUDIT.md','replay-audit-review.md'),
                            ('docs/STRATEGY_FINDINGS.md','strategy-findings.md')]:
        require(saved[bundled] == (evidence / public).read_bytes(), 'Review download differs')
    if (root / 'research_results/2026-10-12-v2/plan.json').is_file():
        for name, data in saved.items():
            path = root / name
            require(path.is_file() and not path.is_symlink() and data == path.read_bytes(), f'Expanded bundled/source mismatch: {name}')


def check(root=ROOT):
    if not __debug__:
        raise ValueError("Publication validation requires non-optimized Python")
    root = Path(root)
    dist = root / "dist"
    anchor = json.loads((root / "security" / "approved-publication.json").read_text())
    expected = anchor["publication_files"]
    publication = json.loads((dist / "publication.json").read_text())
    require(publication["application_id"] == "coup.jacobdanderson.net", "Wrong publication identity")
    if (root / "VERSION").is_file():
        require(publication["version"] == (root / "VERSION").read_text().strip(), "Publication version differs from source")
    paths = list(dist.rglob("*"))
    require(not dist.is_symlink() and not any(p.is_symlink() for p in paths), "Publication contains a symlink")
    actual = {p.relative_to(dist).as_posix() for p in paths if p.is_file()}
    require(actual == set(expected), "Publication inventory differs from reviewed anchor")
    for name, metadata in expected.items():
        require(not name.startswith("/") and ".." not in Path(name).parts, "Unsafe anchored path")
        path = dist / name
        require(path.stat().st_size == metadata["size"] and digest(path) == metadata["sha256"],
                f"Publication file changed: {name}")
    html = (dist / "index.html").read_text()
    parser = StudyData()
    parser.feed(html)
    require(html.count('id="study-data"') == 1, "Expected one study data block")
    require(len(parser.scripts) == 2 and not any("src" in s for s in parser.scripts), "Unexpected script")
    policy = json.loads((root / "security" / "site-policy.json").read_text())
    require(isinstance(parser.csp, str) and policy.get('schema_version') == 1 and
            policy.get('static_only') is True and
            policy['headers']['Content-Security-Policy'] ==
            parser.csp + "; frame-ancestors 'none'; upgrade-insecure-requests" and
            policy['headers'].get('X-Content-Type-Options') == 'nosniff' and
            policy['headers'].get('Referrer-Policy') == 'no-referrer' and
            policy['headers'].get('X-Frame-Options') == 'DENY',
            "CSP or required response headers differ")
    require("unsafe-inline" not in parser.csp and "unsafe-eval" not in parser.csp, "Unsafe CSP")
    for script in re.findall(r'<script\b[^>]*>(.*?)</script>', html, re.S):
        value = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        require("'sha256-" + value + "'" in parser.csp, "Script is missing its exact CSP hash")
    embedded = json.loads("".join(parser.data))
    evidence = dist / "evidence"
    screening = verify_panel(evidence, "screening")
    confirmation = verify_panel(evidence, "confirmation")
    findings = json.loads((evidence / "findings.json").read_text())
    require(embedded["screening"] == screening, "Embedded screening differs")
    require(embedded["confirmation"] == confirmation, "Embedded confirmation differs")
    require(embedded["findings"] == findings["findings"], "Embedded findings differ")
    expanded = 'research' in embedded or 'expanded_study_games' in publication
    if expanded:
        require('research' in embedded and 'expanded_study_games' in publication and
                'expanded_research_source_sha256' in anchor,
                'Reviewed anchor does not authorize the expanded study')
        verify_research_bundle(root, evidence, embedded, anchor, publication)
    has_expansion = 'expansion' in embedded or 'expansion_study_games' in publication
    if has_expansion:
        require('expansion' in embedded and 'expansion_configs' in embedded and
                'expansion_study_games' in publication and 'expansion_study' in anchor,
                'Reviewed anchor does not authorize the expansion study')
        # Load the reviewed checker beside this file. Isolated Python omits its
        # directory from sys.path; bundled evidence is never imported or run.
        spec = importlib.util.spec_from_file_location(
            'coup_expansion_publication', ROOT / 'expansion_publication.py')
        require(spec is not None and spec.loader is not None,
                'Expansion publication verifier is unavailable')
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        verifier.verify_expansion_bundle(root, evidence, embedded, anchor, publication)
    require(sum(int(r["games"]) for r in screening) == findings["screening_games"], "Screening total differs")
    require(sum(int(r["games"]) for r in confirmation) == findings["confirmation_games"], "Confirmation total differs")
    plan = json.loads((evidence / "confirmation-plan.json").read_text())
    require(digest(evidence / "screening-results.csv") == plan["screening_results_sha256"], "Selection plan input differs")
    require('lang="en"' in html and '<caption id="table-caption">' in html, "Accessibility structure differs")
    require('<label>Players <select id="players-select"' in html, "Players label missing")
    if expanded:
        for element_id in ('research-players', 'research-field', 'research-body',
                           'research-caption', 'research-comparison', 'research-bounds',
                           'research-robust-body', 'counter-body', 'ablation-cards'):
            require(html.count(f'id="{element_id}"') == 1,
                    f'Expanded results element differs: {element_id}')
    if has_expansion:
        for element_id in ('rules-profile', 'study-scope', 'base-results',
                           'expansion-results', 'expansion-players', 'expansion-field',
                           'expansion-stage', 'expansion-strategy', 'expansion-body',
                           'expansion-broad-body', 'expansion-counter-body',
                           'expansion-pair', 'expansion-bounds'):
            require(html.count(f'id="{element_id}"') == 1,
                    f'Expansion results element differs: {element_id}')
    require(not re.search(r'__[A-Z][A-Z0-9_]*__', html),
            'Unfilled site template marker')
    for href in re.findall(r'href="\./([^"]+)"', html):
        require((dist / href).is_file(), f"Broken local link: {href}")
    for name, expected_hash in anchor["research_source_sha256"].items():
        require(digest(evidence / name) == expected_hash, f"Reviewed research source changed: {name}")
    # A full source checkout also must match the bundled snapshot. Extracted
    # release archives intentionally contain only dist plus external controls.
    if (root / "study_manifest.json").is_file():
        copies = {"screening-results.csv": "results.csv", "screening-seats.csv": "benchmark_results.csv",
                  "screening-games.csv": "games.csv", "screening-manifest.json": "study_manifest.json",
                  "confirmation-results.csv": "confirmation/results.csv", "confirmation-seats.csv": "confirmation/benchmark_results.csv",
                  "confirmation-games.csv": "confirmation/games.csv", "confirmation-manifest.json": "confirmation/study_manifest.json",
                  "confirmation-plan.json": "confirmation_plan.json", "findings.json": "findings.json",
                  "source-ledger.md": "SOURCE_LEDGER.md", "coup_simulator.py": "coup_simulator.py",
                  "run_experiments.py": "run_experiments.py", "test_coup_simulator.py": "test_coup_simulator.py"}
        for destination, source in copies.items():
            require((evidence / destination).read_bytes() == (root / source).read_bytes(), f"Bundled/source mismatch: {source}")
    print(f"Verified {len(expected)} publication files, raw outcomes, source hashes, embedded data, and CSP.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    check(args.root)
