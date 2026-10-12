# Coup Strategy Lab

A reproducible simulator and results page for the standard Coup bluffing game. The frozen rules engine models the five roles, all base actions, challenges, counteractions, influence loss, exchanges, and the two-player starting-coin rule. The expanded study adds card-aware decisions, conditional bluffs, public-history learning, threat targeting, adaptive card retention, and finite parameter tuning. Results identify which **tested policy** performed well in a named simulated matchup; they do not solve human Coup.

Open [the local findings page](dist/index.html) after running the commands below. Expanded conclusions are in [docs/STRATEGY_FINDINGS.md](docs/STRATEGY_FINDINGS.md), with precise paired results in [the expanded findings](research_results/2026-10-12-v2/FINDINGS.md). The initial study remains in [FINDINGS.md](FINDINGS.md). The rule sources are listed in [SOURCE_LEDGER.md](SOURCE_LEDGER.md).

## Expanded strategy research

The independent design and strategic reasoning are in [docs/RESEARCH_DESIGN.md](docs/RESEARCH_DESIGN.md) and [docs/STRATEGY_REVIEW.md](docs/STRATEGY_REVIEW.md). The source protocol was committed before any new outcomes in `12ab9e1`. The rejected initial protocol in `research_results/2026-10-12/` generated no games and is preserved with its explanation.

The expanded study contains **2,814,728 games**, including **2,240,000 untouched confirmation games**, across seven stages. Independent audits reconciled every raw outcome and freshly replayed **26,912 games** with exact winner and turn agreement. Full verification scope is in [docs/VALIDATION.md](docs/VALIDATION.md).

The separately frozen expanded study lives in [research_results/2026-10-12-v2/](research_results/2026-10-12-v2/). It separates parameter tuning, contender screening, untouched confirmation across 2–6 players and seven fields, counter search and fresh counter confirmation, component removals, and heterogeneous stress tests. Every action receives explicit card, influence, coin, and elimination checks. Distinct focal identities rotate through all seats; decisions use random streams separate from the deck. Learning resets per game. Raw compressed outcomes, exact parameters, source fingerprints, plans, seat diagnostics, and file hashes are retained.

Confirmation compares the top two **selected in screening**, with simultaneous bounds across 35 comparisons. Counter and component tests have separate families of four and 56 comparisons. Both approximate normal and conservative Hoeffding bounds are reported. An observed leader or approximate separation is not a universal winner. See the [expanded findings](research_results/2026-10-12-v2/FINDINGS.md) and the independently reconstructed [replay audit](docs/REPLAY_AUDIT.md).

To rerun the complete protocol into a new directory and independently audit it:

```sh
python3 -B run_strategy_research.py --output-dir ./research_results/my-study --freeze-only
python3 -B run_strategy_research.py --output-dir ./research_results/my-study --workers 4
python3 -B analyze_strategy_research.py --study-dir ./research_results/my-study
python3 -B scripts/audit_research_replay.py --help
```

The runner rejects changed plans or execution source on resume and checks cached summaries against raw games before selection. Do not edit execution modules and resume an existing panel. Use a new output directory for changed research. The new research protocol separates decision randomness for the original controls too, so original and expanded rates should be interpreted within their respective studies.

## Preserved initial evidence

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

## Initial policy model choices

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
| [research_strategies.py](research_strategies.py) | Richer public-information policies and frozen parameter configurations |
| [run_strategy_research.py](run_strategy_research.py) | Seven separate research stages with immutable plans and compressed raw games |
| [research_statistics.py](research_statistics.py) | Paired rotation-block comparisons and simultaneous uncertainty bounds |
| [analyze_strategy_research.py](analyze_strategy_research.py) | Frozen independent raw outcome analyzer |
| [verify_strategy_research.py](verify_strategy_research.py) | Portable delivery audit with exact discrete evidence |
| [scripts/audit_research_replay.py](scripts/audit_research_replay.py) | Independent lineup reconstruction and strict saved-game replays |
| [build_site.py](build_site.py) | Builds the static local recap and evidence bundle |
| [check_site.py](check_site.py) | Checks page data and downloaded files against the frozen study |
| [dist/index.html](dist/index.html) | Interactive result table, rules, method, and downloads |

## GitHub and publication

Public source: [anderson-webops/coup.jacobdanderson.net](https://github.com/anderson-webops/coup.jacobdanderson.net). Intended custom domain: [coup.jacobdanderson.net](https://coup.jacobdanderson.net). Source delivery and a GitHub release do not establish domain activation.

The complete static site is tracked in `dist/`. It has no application server, package dependencies, accounts, or writable state. Its small browser script filters frozen result tables. `security/site-policy.json` permits only the exact inline script hashes and supplies the required hosting headers. `security/approved-publication.json` pins the complete reviewed publication inventory and research sources.

Before delivery, run:

```sh
python3 -B -m unittest -v test_coup_simulator test_extensive_rules test_research_strategies test_research_statistics test_strategy_research test_analyze_strategy_research test_verify_strategy_research test_site scripts.test_release_artifact
python3 -B verify_strategy_research.py
python3 -I -B check_site.py
```

A clean committed checkout can build and verify the deterministic release archive, manifest, and checksums using `scripts/release_artifact.py`. Only the archive's `dist/` contents belong in the public root. The source-to-host contract and protected operator onboarding requirements are in [docs/PUBLICATION.md](docs/PUBLICATION.md). Preserve both IPv4 and IPv6 hosting. Production activation is performed by protected server automation.

The 11 October divergent draft and its inaccurate provenance claims are preserved in `archive/unvalidated-regression-draft-2026-10-11/`. They are excluded from the active study and public site; see [RESULTS_PROVENANCE.md](RESULTS_PROVENANCE.md).

The frozen 122-test suite is supplemented by eleven delivery compatibility tests. See [cross-version verification](docs/RESEARCH_PORTABILITY.md); all scientific source and public evidence bytes remain frozen.
