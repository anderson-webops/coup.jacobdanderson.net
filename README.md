# Coup Strategy Lab

A reproducible simulator and local results page for the standard Coup bluffing game. The engine models the five roles, all base actions, challenges, counteractions, influence loss, exchanges, and the two-player starting-coin rule. It compares eleven explicit policy heuristics under named opponent fields. The results answer which **tested policy** won most often in each simulated matchup; they do not solve human Coup.

Open [the local findings page](dist/index.html) after running the commands below. Research conclusions and precise limitations are in [FINDINGS.md](FINDINGS.md). The rule sources are listed in [SOURCE_LEDGER.md](SOURCE_LEDGER.md).

## Current evidence

- Screening: **88,000 games** across 2–6 players, eleven policies, and four opponent fields. Nine games reached the 1,000-action cap.
- Held-out confirmation: **168,000 four-player games** on a separate seed panel, testing the union of each field's screening top three plus baseline. Seventeen games reached the cap.
- Each candidate takes every seat equally often. The focal player is tracked by seat identity, including in games where several players share a policy name.
- The active results are [results.csv](results.csv), [benchmark_results.csv](benchmark_results.csv), [games.csv](games.csv), [study_manifest.json](study_manifest.json), and the corresponding files in [confirmation/](confirmation/). Initial CSVs with known attribution and rules errors are retained only in [archive/invalid-initial-results-2026-10-10/](archive/invalid-initial-results-2026-10-10/).

## Reproduce

Python 3.10 or newer is sufficient. No third-party packages are required.

```sh
python3 -B -m unittest -v test_coup_simulator.py
python3 -B run_experiments.py --games-per-seat 100 --players 2 3 4 5 6 --panel 0 --output-dir .
python3 -B run_experiments.py --games-per-seat 1500 --players 4 --panel 1 --candidates baseline block_aggressive bluff_heavy challenge_heavy challenge_low exchange taxer --output-dir ./confirmation
python3 -B analyze_results.py
python3 -B build_site.py
python3 -B check_site.py
```

The second run's candidates are frozen in [confirmation_plan.json](confirmation_plan.json), alongside the screening result hash and selection rule. The runner writes its own CSV files; do not redirect its standard output to a result file. It uses the same seed for each candidate at a given player count, opponent field, seat, and game index. Panel 1 adds a disjoint seed offset. Both manifests record source and result SHA-256 hashes. [findings.json](findings.json) records paired top-two comparisons with simultaneous 95% intervals across the four preselected fields.

For a quick custom panel, use:

```sh
python3 -B run_experiments.py --games-per-seat 50 --players 4 --fields mixed --candidates baseline taxer exchange --panel 2 --output-dir ./custom-panel
```

Use a different output directory for a custom run so the frozen evidence remains intact.

## Model choices

The base rulebook requires a Coup at **10** coins. All supplied policies choose to Coup as soon as they have **7**, a shared strategic choice. The baseline only claims roles it holds. It prefers Tax with Duke, Steal with Captain, occasional Exchange with Ambassador, and otherwise Foreign Aid; it challenges claims that are impossible given its own cards and revealed cards. Other policies change one or more action, challenge, or block choices. Exact descriptions appear in [FINDINGS.md](FINDINGS.md) and on the page.

A legal-information boundary exposes a policy's own cards, public coins, influence counts, and revealed cards. It does not expose opponents' hidden cards or the court deck. When multiple players could respond, the engine resolves them clockwise for reproducibility; the rulebook does not impose that priority. A player with a claimed card always proves it if challenged. All policies use the same simple target and influence-loss heuristics. After two failed actions, a policy takes Income once to escape common programmed loops.

The model omits negotiations, nonbinding deals, expansion roles, team rules, and the optional two-player card setup. It does not model a finite Treasury supply or a human player's choice to decline proof of a held card. A turn-limit draw is reported as a draw and remains in the win-rate denominator. The two-player first seat starts with one coin, so those rows should be viewed separately from 3–6-player comparisons.

## Files

| File | Purpose |
| --- | --- |
| [coup_simulator.py](coup_simulator.py) | Rules engine and named policies |
| [test_coup_simulator.py](test_coup_simulator.py) | Focused rule regressions and card-conservation checks |
| [run_experiments.py](run_experiments.py) | Seat-balanced panels, raw outcomes, intervals, and manifests |
| [benchmark_policies.py](benchmark_policies.py) | Supplemental heterogeneous-lineup runner with explicit player identity |
| [analyze_results.py](analyze_results.py) | Checks frozen evidence and calculates paired differences |
| [build_site.py](build_site.py) | Builds the static local recap and evidence bundle |
| [check_site.py](check_site.py) | Checks page data and downloaded files against the frozen study |
| [dist/index.html](dist/index.html) | Interactive result table, rules, method, and downloads |
