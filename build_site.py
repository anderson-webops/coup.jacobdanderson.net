"""Build the local static Coup findings page from validated study evidence."""
from __future__ import annotations

import csv
import base64
import hashlib
import gzip
import io
import json
import re
import shutil
import tarfile
from pathlib import Path

from analyze_results import verify_manifest
from verify_strategy_research import verify_research
from check_site import verify_research_findings
from expansion_publication import build_expansion_publication

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
EVIDENCE = DIST / "evidence"
RESEARCH = ROOT / "research_results" / "2026-10-12-v2"
RESEARCH_ROOT_FILES = {'plan.json', 'selection.json', 'counter_selection.json',
                       'findings.json', 'FINDINGS.md', 'replay-audit.json'}
RESEARCH_DOCS = ('docs/STRATEGY_REVIEW.md', 'docs/RESEARCH_DESIGN.md',
                 'docs/RULES_TEST_REVIEW.md', 'docs/REPLAY_AUDIT.md',
                 'docs/STRATEGY_FINDINGS.md')


def checked_research_files():
    """Include only the audited research files, never work files or links."""
    if RESEARCH.is_symlink():
        raise ValueError('Research directory is a symlink')
    observed = set()
    for path in RESEARCH.rglob('*'):
        if path.is_symlink():
            raise ValueError(f'Research contains symlink: {path}')
        if path.is_file():
            observed.add(path.relative_to(RESEARCH).as_posix())
    plan = json.loads((RESEARCH / 'plan.json').read_text())
    expected = set(RESEARCH_ROOT_FILES)
    for stage in plan['seed_namespaces']:
        stage_manifest = json.loads((RESEARCH / stage / 'manifest.json').read_text())
        expected.update(f'{stage}/{name}' for name in
                        ({'manifest.json'} | set(stage_manifest['files'])))
    if observed != expected:
        raise ValueError(f'Research inventory differs: missing={sorted(expected-observed)[:5]}, '
                         f'extra={sorted(observed-expected)[:5]}')
    return {f'research_results/2026-10-12-v2/{name}': RESEARCH / name
            for name in sorted(expected)}


def research_bundle():
    """Deterministic, downloadable evidence; never execute bundled source."""
    source_files = json.loads((RESEARCH / 'plan.json').read_text())['source_sha256']
    files = checked_research_files()
    files.update({name: ROOT / name for name in source_files})
    for name in RESEARCH_DOCS:
        files[name] = ROOT / name
    files['scripts/audit_research_replay.py'] = ROOT / 'scripts/audit_research_replay.py'
    for name, file in files.items():
        if not file.is_file() or file.is_symlink():
            raise ValueError(f'Research bundle input is missing or linked: {name}')
        for parent in file.parents:
            if parent == ROOT:
                break
            if parent.is_symlink():
                raise ValueError(f'Research bundle path has a linked directory: {name}')
    manifest = {name: {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'size': path.stat().st_size}
                for name, path in sorted(files.items())}
    if sum(item['size'] for item in manifest.values()) > 128 * 1024 * 1024:
        raise ValueError('Research bundle exceeds reviewed size bound')
    path = EVIDENCE / 'research-evidence.tar.gz'
    temporary = path.with_name(path.name + '.part')
    with temporary.open('wb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode='w') as archive:
                for name, file in sorted(files.items()):
                    data = file.read_bytes()
                    info = tarfile.TarInfo(name)
                    info.size = len(data); info.mode = 0o644; info.mtime = 0
                    info.uid = info.gid = 0; info.uname = info.gname = ''
                    archive.addfile(info, io.BytesIO(data))
    for name, file in files.items():
        if hashlib.sha256(file.read_bytes()).hexdigest() != manifest[name]['sha256']:
            raise ValueError(f'Research input changed during bundle: {name}')
    temporary.replace(path)
    (EVIDENCE / 'research-bundle-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def main() -> dict:
    verify_manifest(ROOT)
    verify_manifest(ROOT / "confirmation")
    findings = json.loads((ROOT / "findings.json").read_text())
    research = json.loads((RESEARCH / 'findings.json').read_text())
    audited_research, _ = verify_research(RESEARCH)
    if research != audited_research:
        raise ValueError('Expanded findings differ from audited raw outcomes')
    verify_research_findings(research, read_csv(RESEARCH / 'confirmation' / 'summaries.csv'))
    receipt = json.loads((RESEARCH / 'replay-audit.json').read_text())
    plan = json.loads((RESEARCH / 'plan.json').read_text())
    if (receipt.get('status') != 'passed' or
            receipt.get('global_plan_sha256') != hashlib.sha256((RESEARCH / 'plan.json').read_bytes()).hexdigest() or
            receipt.get('source_sha256') != plan['source_sha256'] or
            receipt.get('audit_source_sha256') != hashlib.sha256((ROOT / 'scripts/audit_research_replay.py').read_bytes()).hexdigest() or
            receipt.get('total_raw_games') != research['total_games'] or
            [entry.get('stage') for entry in receipt.get('stages', [])] != plan['seed_namespaces'] or
            receipt.get('total_replayed_games') != sum(entry.get('replayed_games', 0) for entry in receipt['stages']) or
            receipt.get('total_replayed_games', 0) <= 0):
        raise ValueError('Expanded independent replay receipt differs from audited study')
    for stage_entry in receipt['stages']:
        stage = stage_entry['stage']
        if (stage_entry.get('stage_plan_sha256') != hashlib.sha256((RESEARCH / stage / 'plan.json').read_bytes()).hexdigest() or
                stage_entry.get('stage_manifest_sha256') != hashlib.sha256((RESEARCH / stage / 'manifest.json').read_bytes()).hexdigest() or
                stage_entry.get('raw_games') != research['stages'][stage]['games'] or
                stage_entry.get('jobs') != research['stages'][stage]['jobs'] or
                stage_entry.get('replayed_games', 0) <= 0):
            raise ValueError(f'Expanded replay receipt differs for {stage}')
    screening = read_csv(ROOT / "results.csv")
    confirmation = read_csv(ROOT / "confirmation" / "results.csv")
    if sum(int(row["games"]) for row in screening) != findings["screening_games"]:
        raise ValueError("screening counts changed")
    if sum(int(row["games"]) for row in confirmation) != findings["confirmation_games"]:
        raise ValueError("confirmation counts changed")
    if len(findings["findings"]) != 4:
        raise ValueError("expected one finding for each field")
    data = {
        "screening": screening,
        "confirmation": confirmation,
        "findings": findings["findings"],
        "research": research,
        "research_configs": plan['configurations'],
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    expansion = build_expansion_publication(ROOT, EVIDENCE)
    data.update({key: expansion[key] for key in ('expansion', 'expansion_configs')})
    template = (ROOT / "site_template.html").read_text()
    embedded = json.dumps(data, separators=(",", ":")).replace("<", "\\u003c")
    html = (template
            .replace("__SCREEN_GAMES__", f'{findings["screening_games"]:,}')
            .replace("__CONFIRM_GAMES__", f'{findings["confirmation_games"]:,}')
            .replace("__RESEARCH_GAMES__", f'{research["total_games"]:,}')
            .replace("__RESEARCH_CONFIRM_GAMES__", f'{research["stages"]["confirmation"]["games"]:,}')
            .replace("__STUDY_DATA__", embedded))
    if "__STUDY_DATA__" in html or "__SCREEN_GAMES__" in html or "__CONFIRM_GAMES__" in html:
        raise ValueError("unfilled site template")
    script_hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'"
                     for script in re.findall(r'<script\b[^>]*>(.*?)</script>', html, re.S)]
    csp = ("default-src 'none'; base-uri 'none'; object-src 'none'; form-action 'none'; "
           "img-src 'self'; style-src 'self'; script-src " + " ".join(script_hashes) + "; connect-src 'none'")
    html = html.replace("__CONTENT_SECURITY_POLICY__", csp)
    if re.search(r'__[A-Z][A-Z0-9_]*__', html):
        raise ValueError('Unfilled site template marker')
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    copies = {
        "screening-results.csv": ROOT / "results.csv",
        "screening-seats.csv": ROOT / "benchmark_results.csv",
        "screening-games.csv": ROOT / "games.csv",
        "screening-manifest.json": ROOT / "study_manifest.json",
        "confirmation-results.csv": ROOT / "confirmation" / "results.csv",
        "confirmation-seats.csv": ROOT / "confirmation" / "benchmark_results.csv",
        "confirmation-games.csv": ROOT / "confirmation" / "games.csv",
        "confirmation-manifest.json": ROOT / "confirmation" / "study_manifest.json",
        "confirmation-plan.json": ROOT / "confirmation_plan.json",
        "findings.json": ROOT / "findings.json",
        "source-ledger.md": ROOT / "SOURCE_LEDGER.md",
        "coup_simulator.py": ROOT / "coup_simulator.py",
        "run_experiments.py": ROOT / "run_experiments.py",
        "test_coup_simulator.py": ROOT / "test_coup_simulator.py",
        'research-findings.json': RESEARCH / 'findings.json',
        'research-confirmation.csv': RESEARCH / 'confirmation' / 'summaries.csv',
        'research-replay-audit.json': RESEARCH / 'replay-audit.json',
        'research-design.md': ROOT / 'docs' / 'RESEARCH_DESIGN.md',
        'strategy-review.md': ROOT / 'docs' / 'STRATEGY_REVIEW.md',
        'rules-test-review.md': ROOT / 'docs' / 'RULES_TEST_REVIEW.md',
        'replay-audit-review.md': ROOT / 'docs' / 'REPLAY_AUDIT.md',
        'strategy-findings.md': ROOT / 'docs' / 'STRATEGY_FINDINGS.md',
        'research_strategies.py': ROOT / 'research_strategies.py',
    }
    for destination, source in copies.items():
        shutil.copy2(source, EVIDENCE / destination)
    research_bundle()
    (DIST / "index.html").write_text(html)
    shutil.copy2(ROOT / "site.css", DIST / "site.css")
    shutil.copy2(ROOT / "favicon.svg", DIST / "favicon.svg")
    (DIST / "publication.json").write_text(json.dumps({
        "application_id": "coup.jacobdanderson.net", "version": (ROOT / "VERSION").read_text().strip(),
        "research_snapshot": "2026-10-12", "initial_research_snapshot": "2026-10-10", "screening_games": findings["screening_games"],
        "confirmation_games": findings["confirmation_games"],
        'expanded_study_games': research['total_games'],
        'expanded_confirmation_games': research['stages']['confirmation']['games'],
        **expansion['publication'],
    }, indent=2) + "\n")
    (ROOT / "security").mkdir(exist_ok=True)
    (ROOT / "security" / "site-policy.json").write_text(json.dumps({
        "schema_version": 1,
        "headers": {
            "Content-Security-Policy": csp + "; frame-ancestors 'none'; upgrade-insecure-requests",
            "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
            "X-Frame-Options": "DENY",
        },
        "static_only": True,
    }, indent=2) + "\n")
    for href in re.findall(r'href="\./evidence/([^"]+)"', html):
        if not (EVIDENCE / href).is_file():
            raise ValueError(f"broken evidence link: {href}")
    if html.count('class="finding-card"') != 0:
        raise ValueError("finding cards should be populated from the frozen data")
    print(f"Built {DIST / 'index.html'} with preserved base evidence and "
          f"{expansion['expansion']['total_games']:,} expansion games")
    return {'expansion_study': expansion['anchor'], **expansion['publication']}


if __name__ == "__main__":
    main()
