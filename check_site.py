"""Validate the exact static publication and its reproducible study evidence."""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


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
    require(policy["headers"]["Content-Security-Policy"].startswith(parser.csp + ";"), "CSP differs from header policy")
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
    require(sum(int(r["games"]) for r in screening) == findings["screening_games"], "Screening total differs")
    require(sum(int(r["games"]) for r in confirmation) == findings["confirmation_games"], "Confirmation total differs")
    plan = json.loads((evidence / "confirmation-plan.json").read_text())
    require(digest(evidence / "screening-results.csv") == plan["screening_results_sha256"], "Selection plan input differs")
    require('lang="en"' in html and '<caption id="table-caption">' in html, "Accessibility structure differs")
    require('<label>Players <select id="players-select"' in html, "Players label missing")
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
