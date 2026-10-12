"""Build the local static Coup findings page from validated study evidence."""
from __future__ import annotations

import csv
import base64
import hashlib
import json
import re
import shutil
from pathlib import Path

from analyze_results import verify_manifest

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
EVIDENCE = DIST / "evidence"


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def main() -> None:
    verify_manifest(ROOT)
    verify_manifest(ROOT / "confirmation")
    findings = json.loads((ROOT / "findings.json").read_text())
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
    }
    template = (ROOT / "site_template.html").read_text()
    embedded = json.dumps(data, separators=(",", ":")).replace("<", "\\u003c")
    html = (template
            .replace("__SCREEN_GAMES__", f'{findings["screening_games"]:,}')
            .replace("__CONFIRM_GAMES__", f'{findings["confirmation_games"]:,}')
            .replace("__STUDY_DATA__", embedded))
    if "__STUDY_DATA__" in html or "__SCREEN_GAMES__" in html or "__CONFIRM_GAMES__" in html:
        raise ValueError("unfilled site template")
    script_hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'"
                     for script in re.findall(r'<script\b[^>]*>(.*?)</script>', html, re.S)]
    csp = ("default-src 'none'; base-uri 'none'; object-src 'none'; form-action 'none'; "
           "img-src 'self'; style-src 'self'; script-src " + " ".join(script_hashes) + "; connect-src 'none'")
    html = html.replace("__CONTENT_SECURITY_POLICY__", csp)
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
    }
    for destination, source in copies.items():
        shutil.copy2(source, EVIDENCE / destination)
    (DIST / "index.html").write_text(html)
    shutil.copy2(ROOT / "site.css", DIST / "site.css")
    shutil.copy2(ROOT / "favicon.svg", DIST / "favicon.svg")
    (DIST / "publication.json").write_text(json.dumps({
        "application_id": "coup.jacobdanderson.net", "version": (ROOT / "VERSION").read_text().strip(),
        "research_snapshot": "2026-10-10", "screening_games": findings["screening_games"],
        "confirmation_games": findings["confirmation_games"],
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
    print(f"Built {DIST / 'index.html'} with {len(screening)} screening rows and {len(confirmation)} confirmation rows")


if __name__ == "__main__":
    main()
