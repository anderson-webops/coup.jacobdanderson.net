# Coup strategy research design

Status: implementation protocol. Freeze exact policy configurations, rosters, sample counts, comparisons, and seeds in a versioned plan before running each panel. This document does not revise the validated 10 October 2026 study. Its screening and confirmation manifests, CSVs, source fingerprints, and public evidence remain separate.

## Question and scope

Which **tested** Coup policies win most often under standard base-game rules, for a stated player count and a stated population of opponents? Which policies counter a named target, and which components of a stronger policy appear to matter? A finite simulator cannot identify an unrestricted optimal strategy or predict human table talk.

The new study covers two through six players. The standard three-through-six-player game is the main interpretation; two-player results retain the rulebook's asymmetric starting coin and are reported separately. Every policy receives its own hidden cards and public events only. No policy receives the deck order, opponent hidden cards, unobserved challenge truth, or an opponent's strategy label. An adaptive policy resets memory at the start of every game unless a separate, explicit cross-game-learning experiment is planned.

## Why the first four fields are insufficient

The first frozen study usefully tested honest, always-bluffing, always-challenging, and a simple mixed field. These are sharp stress cases, but they do not cover selective challenges, conditional bluffs, opponents that update beliefs, or ordinary randomized play. Its confirmation involved four players only. Its seven finalists were chosen from that simpler environment. The new study should not treat the earlier field winners as a ceiling on strategy quality. It should include them as controls and compare them to stronger, explicitly defined opponents at every player count.

## Policy families to build and test

Preserve the eleven named controls from the first study. Add a small, interpretable set of parameterized families, each with a stable configuration ID and exact JSON parameters:

1. **Card-aware economy:** choose Income, Foreign Aid, truthful Tax, Steal, Assassinate, Exchange, or Coup from public coin and influence state. Vary Coup timing from seven to ten coins while enforcing a Coup at ten.
2. **Conditional bluffing:** claim Tax, Steal, or a block only when expected reward exceeds the estimated challenge and retaliation cost. Vary bluff probability and risk tolerance without using hidden truth.
3. **Selective challenge:** combine card-copy impossibility with a threshold on an opponent's claim credibility, action value, and remaining influence. Include a conservative version that challenges only impossible claims and a pressure version that takes greater risk when behind.
4. **Public-belief policy:** update role plausibilities from the 15-card prior, the policy's own cards, revealed losses, shown-and-replaced cards, public claims, and public challenge outcomes. Treat unproved claims as evidence with configurable reliability, never as certain hidden-card knowledge.
5. **Within-game response learner:** maintain a bounded prior and update each opponent's observed challenge, block, and bluff behavior from public events. Reset every game and never read the opponent's implementation label.
6. **Survival and targeting:** protect a single remaining influence, value defensive cards when assassination risk is high, and target a visible immediate threat rather than always selecting a random opponent.
7. **Exchange-aware keeper:** value role pairs using current coins, revealed copies, likely threats, and action opportunities. Preserve the current influence count and all card copies on every exchange.
8. **Seeded legal random:** sample from legal actions and responses under a frozen distribution. This is an opponent control, not a claim that random play is strong.

Keep policies decomposable: action, target, challenge, block, influence-loss choice, and exchange keep. An ablation can then turn off one component without changing unrelated parameters. Search a bounded grid or seeded random sample of policy settings. Log rejected, illegal, or duplicate configurations before simulation. Tune parameters only on the development panel.

## Opponent fields and lineup balance

Freeze seven primary fields before screening: honest (`baseline`), bluffing (`bluff_heavy`), skeptical (`challenge_heavy`), rational (`card_balanced`), learning (`public_learning`), random (`public_random`), and mixed. The exact versioned plan defines every field's policy configuration and how its `players - 1` opponents are chosen.

For homogeneous fields all opponents use the named policy. The mixed field cycles through `baseline`, `bluff_heavy`, `challenge_heavy`, `card_balanced`, `public_learning`, `public_random`, and `eliminator`, with identities and order chosen by the frozen block schedule. At two players, a mixed block samples one type; counts differ by at most one over complete cycles. At higher player counts, composition and order vary with block. Never silently call a two-player baseline-only matchup a mixed field. Distinguish repeated copies of the same policy by participant identity.

For each candidate, player count, field, and random block, rotate the focal **identity** through every seat. Use the same initial seed and opponent-order assignment for every candidate in a paired block. Common seeds make comparisons more precise but do not make later random trajectories identical after policies choose different actions. Report seat rates separately as a diagnostic, while treating the complete rotation block as the independent unit for inference.

## Staged experiment

The numbers below are a bounded starting budget. The frozen plan must record the exact counts and deterministic selection rules before execution. Let `K` be the number of candidates carried into a stage. A cell's game count is `player_count × blocks × K`; sum that over fields and player counts. Stop at the planned budget and report an unresolved comparison when precision is insufficient.

| Panel | Purpose | Coverage and provisional size | Selection and use |
| --- | --- | --- | --- |
| A, development | Check new policies and tune parameters | Twenty-four finite parameter configurations; two, four, six players; all seven fields; 32 complete blocks, 64,512 scheduled games | Search and debug only. No confirmation claims. |
| B, screening | Select contenders and counter targets | Six global A tuners, seven named advanced policies, and eleven old controls, at most 24 candidates; two through six players; all seven fields; 100 blocks, at most 336,000 games | Freeze the top two by observed block-balanced win rate per player-count/field cell, three required controls, and two named counter targets. Preserve all B results. |
| C, confirmation | Estimate performance on unseen randomness | Two through six players; all seven fields; 1,000 blocks for the union of the 35 B-selected top-two lists plus `baseline`, `card_balanced`, and `public_learning` | Run the same union in every cell. Every union member gets 140,000 games; with at most 24 B candidates this is at most 3,360,000 games. Compare the two **B-selected** finalists in each of the 35 cells, even if a different candidate ranks first in C. No hidden union cap, retuning, or pair reselection. |
| D, counters | Test a named best response | Two targets chosen in B, two and four players; D screening at 32 blocks, then a fresh D confirmation at 1,000 blocks | Screen candidate counters against each frozen target, select one per target/player-count setting using D screening only, then confirm on new seeds. Report the counter's win rate against target copies, its `1 / player_count` self-play reference, and a paired target-control contrast. |
| E, ablations | Attribute modeled components | `public_learning` against `ablate_no_claim_cards`, `ablate_no_history`, `ablate_random_target`, and `ablate_fixed_retention`; two and four players; all seven fields; 500 blocks | Freeze all four components before E; compare full and disabled versions on matched panels. The primary family has 56 contrasts. Interpret as local simulation effects. |
| F, stress | Inspect interactions omitted by focal-versus-field cells | Six-player self-play and named heterogeneous stress lineups; 100 complete blocks per lineup | Treat as a separate descriptive stress panel. It cannot change C's predeclared comparison family or candidate set. |

Panels A, B, C, D screening, D confirmation, E, and F use disjoint seed namespaces. A policy that learns during a game starts each game from the same frozen prior. Do not carry learning from earlier simulated games into later panels. If a new counter is discovered after B, mark it exploratory, retest an enlarged population on a new selection panel, and reserve another untouched confirmation panel before calling it confirmed.

## Outcomes and uncertainty

The primary descriptive metric is focal wins divided by **all scheduled games**; capped games count as draws in that denominator. Report draws, cap rate, mean turns, seat rates, and candidate policy configuration. Show each candidate's results within each player-count/field cell. Do not rank across player counts by raw win rate: the symmetric reference is `1 / player_count`.

For each predeclared pair, compute one focal win fraction per complete rotation block and subtract the two candidates' block fractions. The mean paired difference is the effect estimate. `research_statistics.py` rejects duplicate games, missing rotations, repeated focal seats, inconsistent winner flags, reused block seeds, and nonidentical paired seed panels. It reports a Bonferroni-adjusted normal interval over block differences for the **fixed family of 35 primary comparisons**. That interval is approximate. It also reports a conservative Hoeffding/union-bound interval using the paired block range of `[-1, 1]`, as in the spirit of the Liar's Dice study. Counter and ablation families use their own frozen sizes, four target/count settings and 56 component/count/field contrasts respectively. Near a probability boundary or with low block variation, give the conservative interval special weight. At 1,000 blocks and 35 comparisons, its paired-difference half-width is about 12 points, so small advantages will remain unresolved under that strict bound.

Declare a two-percentage-point absolute win-rate difference as the smallest practically interesting effect before C. A positive lower bound supports a modeled advantage; a lower bound above +0.02 supports a practically meaningful one under that interval method. A point estimate above zero alone is a lead, not evidence of separation. A normal interval that excludes zero while the conservative interval includes zero is labeled **approximate evidence**, not a robustly established winner. Maintain separate predeclared comparison families for counters and ablations; record their actual family sizes and do not choose pairs from those panels after looking at their outcomes.

Also report each candidate's equally weighted average across the seven fields within a player count, its worst observed field, and a sensitivity scenario that doubles the rational and learning field weights. Those are scenario summaries, not a measured distribution of human opponents. A claim of a broad recommendation requires no material collapse in a named stress field. Direct two-player duels may be represented as a finite empirical payoff matrix; any mixed-strategy recommendation is conditional on that tested matrix and does not extend automatically to multiplayer play.

## Raw-row contract and reproducibility

Store one row per game with `stage,players,field,candidate,block,rotation,seed,winner,focal_seat,won,draw,turns`. `winner` is the winning seat or blank for a draw; `won` is `winner == focal_seat`. Each `(stage, players, field, candidate, block)` has rotations `0..players-1`, one focal visit per seat, and one initial seed. Candidate comparisons require the same block IDs, rotation mapping, seeds, opponent-order plan, and focal seats. The frozen lineup rule assigns unique participant identities `0..players-1`, rotates identity 0 into `focal_seat`, and reconstructs the full lineup from the row coordinates, even when policy names repeat.

Before each panel, save a plan with rules profile, source and policy-config SHA-256 hashes, Python version, candidate IDs, player counts, fields, complete lineup-generation rule, seed namespace, blocks, cap, comparisons, alpha, practical threshold, and output schema. On resume, reject a mismatch in any execution source or plan fingerprint and start a new results directory. Save per-game outcomes, block summaries, action/challenge/block/exchange diagnostics, test results, and output hashes. Independently reconcile row counts and exact key sets against the plan; spot-replay random saved rows and edge-case seeds. Run invariant tests for card conservation, influence count, coin nonnegativity, legal claims and responses, truthful and false challenges, single-influence exchange, and turn termination before treating strategy results as evidence.

## Relationship to Liar's Dice

The Liar's Dice research [plan](</Users/jacobanderson/Library/CloudStorage/Dropbox/Jacobs docs/Docs/Work and School/Programming/Python/PycharmProjects/Fun/LiarsDice/STRATEGY_RESEARCH_PLAN.md>) used separate search, selection, counter, revalidation, and confirmation panels; complete seat rotations; participant identity; frozen source fingerprints; and tested-population wording. Its [results guide](</Users/jacobanderson/Library/CloudStorage/Dropbox/Jacobs docs/Docs/Work and School/Programming/Python/PycharmProjects/Fun/LiarsDice/research_results/2026-09-07/FINDINGS.md>) distinguishes observed leaders from supported paired advantages and reports conservative simultaneous bounds. Coup should reuse those controls while keeping its own hidden-card rules, game dynamics, policies, and outcome evidence.
