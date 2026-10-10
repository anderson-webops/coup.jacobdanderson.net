"""Check that the static page and downloadable evidence match the study."""
from __future__ import annotations

import csv
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"


class StudyData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_study = False
        self.data = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == "study-data":
            self.in_study = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_study = False

    def handle_data(self, data):
        if self.in_study:
            self.data.append(data)


def rows(path: Path) -> list[dict]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def check() -> None:
    html = (DIST / "index.html").read_text()
    parser = StudyData()
    parser.feed(html)
    embedded = json.loads("".join(parser.data))
    findings = json.loads((ROOT / "findings.json").read_text())
    assert embedded["screening"] == rows(ROOT / "results.csv")
    assert embedded["confirmation"] == rows(ROOT / "confirmation" / "results.csv")
    assert embedded["findings"] == findings["findings"]
    assert html.count('id="study-data"') == 1
    assert 'lang="en"' in html and '<caption id="table-caption">' in html
    assert '<label>Players <select id="players-select"' in html
    for name, source in {
        "screening-results.csv": ROOT / "results.csv",
        "screening-games.csv": ROOT / "games.csv",
        "screening-manifest.json": ROOT / "study_manifest.json",
        "confirmation-results.csv": ROOT / "confirmation" / "results.csv",
        "confirmation-games.csv": ROOT / "confirmation" / "games.csv",
        "confirmation-manifest.json": ROOT / "confirmation" / "study_manifest.json",
        "source-ledger.md": ROOT / "SOURCE_LEDGER.md",
        "coup_simulator.py": ROOT / "coup_simulator.py",
        "run_experiments.py": ROOT / "run_experiments.py",
    }.items():
        assert (DIST / "evidence" / name).read_bytes() == source.read_bytes(), name
    for href in re.findall(r'href="\./([^"]+)"', html):
        assert (DIST / href).is_file(), href
    assert (DIST / "site.css").is_file()
    assert (DIST / "favicon.svg").is_file()
    print("Static page, embedded rows, and evidence downloads match frozen study files.")


if __name__ == "__main__":
    check()
