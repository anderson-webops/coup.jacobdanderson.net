# Expanded Coup validation record

The expanded protocol was committed in `12ab9e1` before outcomes. The first,
rejected protocol generated no games and remains separately preserved. The
original 10 October source and results remain byte-for-byte unchanged.

## Outcome verification

The independent analyzer reconciled all **2,814,728 raw game rows**
with stage plans, schedules, source fingerprints, summaries, flags, seat counts,
and selected comparison families. Saved JSON and Markdown findings reproduce
from that audit. A separate checker reconstructed lineups and seed schedules
without importing runner helpers and freshly replayed **26,912
games** across every job. All winners and turn counts matched exactly.

| Stage | Scheduled games | Draws | Fresh strict replays |
| --- | ---: | ---: | ---: |
| ablations | 105,000 | 0 | 660 |
| confirmation | 2,240,000 | 78 | 7,040 |
| counter_search | 9,216 | 9 | 864 |
| counters | 24,000 | 33 | 72 |
| screening | 336,000 | 8 | 10,560 |
| stress | 36,000 | 67 | 1,380 |
| tuning | 64,512 | 0 | 6,336 |

The expanded study has 2,138 jobs and 195 draws. Capped games stay in all win-rate
denominators. Every simulated action received explicit invariant checks.

- Global plan SHA-256: `a8f5312f3cbce265b504a264a85ec4fe9a26a17c23005ca9889167218e46d383`.
- Independent replay receipt SHA-256: `e68ba9b5907eaa9a7b5e6f9458de84264111ae12bdf2ddc1513907f43205bcc1`.
- Audit implementation SHA-256: `dedc9f21d57f38dabfb1f881fae7d8340353c7490fa2f39d1e2d2fe7b85760b4`.

The replay checker shares the frozen rules engine. Independent transition tests
cover rule correctness; replays test saved schedules, identity attribution and
reproducibility. Internal action/event diagnostic counts reconcile with their
saved job files, but the outcome CSV alone cannot independently derive every
internal event tally.

## Automated suite

The frozen research and initial publication suite has **122 test methods**:

| Coverage | Methods |
| --- | ---: |
| Original and independently added rule transitions | 57 |
| Research policies, public-information boundaries and strict game fuzzing | 21 |
| Frozen protocol and paired statistics | 14 |
| Raw-data analysis and saved-findings tamper rejection | 10 |
| Site integrity and immutable release archive | 20 |

The policy tests include 10,000 deterministic strict games across 2–6 players,
plus hidden-state metamorphic checks, fresh-game learning reset, separate
policy/deck randomness, legal affordability, proof replacement and duplicate-safe
Exchange. Tests also reject corrupted summaries, missing rotations, wrong seeds,
false winner flags, changed sources, linked downloads, unsafe archive paths,
changed public evidence and optimized-Python validation.

Eleven additional delivery compatibility methods bring the required suite to **133**. They reject type, numeric, sign, structure, hash, canonical-rendering and ranking drift while preserving all frozen study bytes. See [RESEARCH_PORTABILITY.md](RESEARCH_PORTABILITY.md).

## Final publication gates

The full 133-method delivery suite passed on the completed site, including the 10,000-game
strict policy test. The final analysis verifier again reconciled all 2,814,728
rows and reproduced the saved findings. The portable verifier also passed a full CPython 3.14 audit, with 283 bounded derived-float differences (maximum `3.4694469519536142e-16`), exact discrete results and canonical Markdown. The final site rebuild left every public and frozen research byte unchanged. Isolated static validation
accepted all 29 publication files and their embedded data, downloads, source
hashes and CSP. Optimized Python was explicitly rejected.

Browser review passed all 35 player-count/field selections, all 16 contender
profiles, selection preservation, four counter rows, four component cards and
the original 11-policy screening and seven-policy confirmation controls. At
1440-pixel desktop and 390-pixel phone widths, the page stayed within the viewport;
phone tables scroll inside their containers. Visual screenshots were reviewed.
The browser recorded zero errors and zero warnings under the exact response
policy. The local source/evidence secret scan reported no leaks.

The manually reviewed publication anchor preserves original evidence hashes and
pins the expanded source fingerprints and the complete 29-file inventory.
Clean-commit release build and extracted-tree verification passed at `ef14949540a4c2c251cc95c513509ddb5c530ab5`. GitHub CI 38322612775 passed all required gates. All three Linux CI assets, local assets and GitHub uploaded digests match exactly. The annotated immutable [v1.1.0 release](https://github.com/anderson-webops/coup.jacobdanderson.net/releases/tag/v1.1.0) was published at 23:35:12 UTC on 12 October 2026. See [source/release receipt](validation/v1.1.0-source.json).

Public activation remains separate. At 23:44:24 UTC, direct IPv4 and IPv6 checks still returned the old `1.0.1` publication identity. New-release public acceptance has not been established. Shared Sites/AGENTS.md reserves activation for protected server automation; after activation, all 29 served-byte hashes, required response headers and real 404 must pass over both HTTPS address families. The exact observations and DNS readback are in [public-state receipt](validation/v1.1.0-public-state.json).

## Statistics and strategy presentation, v1.1.1

The focused presentation is released at `3e5ace43c9734c61d5df43a592ab9bdb8311b358`. All 133 tests passed locally and in [exact-source CI 38337042262](https://github.com/anderson-webops/coup.jacobdanderson.net/actions/runs/38337042262), with another complete raw-outcome audit. All 35 main matchups, 560 displayed rows, 16 main profiles, 24 earlier panels and 11 earlier profiles passed browser checks. Desktop and phone views were reviewed at widths 360–1440 pixels without page overflow or browser errors. All frozen research and embedded data bytes are unchanged. See [presentation review](PRESENTATION_REVIEW.md) and [verified source/release receipt](validation/v1.1.1-source.json).

The immutable local, Linux CI and uploaded release assets match. At 2026-10-13T02:36:13Z, both direct HTTPS families still identified version 1.1.0. Public activation of the focused page remains pending protected server automation; full new-release acceptance is not established. See [public-state receipt](validation/v1.1.1-public-state.json).
