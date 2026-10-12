# Coup strategy findings: expanded 12 October 2026 study

The expanded study compares **tested bot policies**, not every possible way to play Coup. Its base-game rules and opponent fields are frozen in the [study plan](../research_results/2026-10-12-v2/plan.json). The [analysis](../research_results/2026-10-12-v2/findings.json) verified 2,814,728 recorded games across seven panels. The [independent replay audit](../research_results/2026-10-12-v2/replay-audit.json) checked every raw row's planned coordinates and replayed 26,912 games with matching winner and turn count. The earlier [10 October study](../FINDINGS.md) remains a separate, narrower experiment.

## What the results support

There is no single winner across opponent types. Under the **honest** field, `bluff_heavy` had the highest observed win rate from two through five players. Against frequent bluffers, `challenge_heavy` led at two and three players. Against opponents who challenge every claim, the `exchange` control led at all five player counts. In the broader mixed field, `exchange` led from three through six players, but its preselected mixed-field pair was unresolved by the conservative interval at every count.

Those are conditional simulator findings. The strongest conservative paired evidence covers only five of the 35 preselected confirmation comparisons. Its clear cases are `challenge_heavy` against frequent bluffers at two and three players, `bluff_heavy` against honest opponents at three and four players, and `bluff_heavy` over `exchange` against the rational field at two players. The remaining point-estimate leads should be read with their intervals below.

## Study size and evidence checks

| Panel | Games | Capped draws | Jobs |
| --- | ---: | ---: | ---: |
| Parameter tuning | 64,512 | 0 | 504 |
| Screening | 336,000 | 8 | 840 |
| Held-out confirmation | 2,240,000 | 78 | 560 |
| Counter search | 9,216 | 9 | 96 |
| Counter confirmation | 24,000 | 33 | 8 |
| Ablations | 105,000 | 0 | 70 |
| Six-player stress | 36,000 | 67 | 60 |
| **Total** | **2,814,728** | **195** | **2,138** |

Draws are 0.0069% of all scheduled games and remain in every win-rate denominator. The confirmation panel tested the same 16 finalists in all 35 combinations of two through six players and seven fields. Each candidate played 1,000 complete seat-rotation blocks per cell, or 2,000 to 6,000 games depending on player count. The 35 compared pairs were selected from the earlier screening panel before confirmation outcomes were generated. The independent audit verified the complete raw-row inventory and spot-replayed the first, middle, and last block of every job, with additional mixed-lineup checks. It is a sample replay of outcomes, not a second simulation of every game.

The seven fields are **honest** (`baseline` opponents), **bluffing** (`bluff_heavy`), **skeptical** (`challenge_heavy`), **rational** (`card_balanced`), **learning** (`public_learning`), **random** (`public_random`, which randomizes actions but retains its regular response rules), and a cyclic **mixed** roster. These are programmed populations, not observed human-player frequencies. The two-player setup has an asymmetric first-seat coin rule; every candidate visited every seat in each block.

## Held-out results by opponent field

The table reports the highest observed candidate among all 16 finalists in each cell, followed by the **screening-selected** pair. The paired difference is the first candidate's win rate minus the second's. “Normal” is an approximate simultaneous 95% interval over the 35 frozen pairs; “conservative” is the corresponding Hoeffding family bound. Both use whole seed-and-seat rotation blocks. A bound excluding zero supports that pair's direction under its method. It does not establish that the observed leader beats every other finalist. `search_08`, `search_21`, and other numbered policies are frozen configurations, not strategies tuned on confirmation outcomes.

| Players | Field | Highest observed (wins/games) | Frozen pair: first vs second | Paired lead | Normal 95% | Conservative 95% | Reading |
| ---: | --- | --- | --- | ---: | --- | --- | --- |
| 2 | honest | `bluff_heavy` 1,638/2,000 (81.9%) | `bluff_heavy` vs `block_aggressive` | +9.45 pp | [+6.82, +12.08] pp | [-2.59, +21.49] pp | Normal only: first |
| 2 | bluffing | `challenge_heavy` 1,585/2,000 (79.2%) | `challenge_heavy` vs `card_bold` | +14.85 pp | [+10.89, +18.81] pp | [+2.81, +26.89] pp | Conservative: first |
| 2 | skeptical | `exchange` 1,644/2,000 (82.2%) | `exchange` vs `baseline` | +7.30 pp | [+5.41, +9.19] pp | [-4.74, +19.34] pp | Normal only: first |
| 2 | rational | `bluff_heavy` 1,615/2,000 (80.8%) | `bluff_heavy` vs `exchange` | +13.35 pp | [+9.76, +16.94] pp | [+1.31, +25.39] pp | Conservative: first |
| 2 | learning | `bluff_heavy` 1,585/2,000 (79.2%) | `bluff_heavy` vs `taxer` | +7.65 pp | [+5.70, +9.60] pp | [-4.39, +19.69] pp | Normal only: first |
| 2 | random | `bluff_heavy` 1,773/2,000 (88.6%) | `bluff_heavy` vs `taxer` | +2.95 pp | [+0.61, +5.29] pp | [-9.09, +14.99] pp | Normal only: first |
| 2 | mixed | `bluff_heavy` 1,314/2,000 (65.7%) | `bluff_heavy` vs `challenge_heavy` | +7.50 pp | [+3.04, +11.96] pp | [-4.54, +19.54] pp | Normal only: first |
| 3 | honest | `bluff_heavy` 2,125/3,000 (70.8%) | `bluff_heavy` vs `taxer` | +16.43 pp | [+14.13, +18.74] pp | [+4.40, +28.47] pp | Conservative: first |
| 3 | bluffing | `challenge_heavy` 1,846/3,000 (61.5%) | `challenge_heavy` vs `search_08` | +26.00 pp | [+22.10, +29.90] pp | [+13.96, +38.04] pp | Conservative: first |
| 3 | skeptical | `exchange` 2,571/3,000 (85.7%) | `exchange` vs `baseline` | +6.20 pp | [+4.74, +7.66] pp | [-5.84, +18.24] pp | Normal only: first |
| 3 | rational | `bluff_heavy` 1,825/3,000 (60.8%) | `bluff_heavy` vs `taxer` | +3.40 pp | [+2.03, +4.77] pp | [-8.64, +15.44] pp | Normal only: first |
| 3 | learning | `bluff_heavy` 1,769/3,000 (59.0%) | `bluff_heavy` vs `taxer` | +3.27 pp | [+2.05, +4.48] pp | [-8.77, +15.30] pp | Normal only: first |
| 3 | random | `search_08` 2,003/3,000 (66.8%) | `search_08` vs `bluff_heavy` | +3.50 pp | [+0.06, +6.94] pp | [-8.54, +15.54] pp | Normal only: first |
| 3 | mixed | `exchange` 1,358/3,000 (45.3%) | `bluff_heavy` vs `exchange` | -0.90 pp | [-5.05, +3.25] pp | [-12.94, +11.14] pp | Unresolved |
| 4 | honest | `bluff_heavy` 2,344/4,000 (58.6%) | `bluff_heavy` vs `block_aggressive` | +15.80 pp | [+12.94, +18.66] pp | [+3.76, +27.84] pp | Conservative: first |
| 4 | bluffing | `search_08` 1,953/4,000 (48.8%) | `search_08` vs `challenge_heavy` | +6.55 pp | [+3.20, +9.90] pp | [-5.49, +18.59] pp | Normal only: first |
| 4 | skeptical | `exchange` 3,399/4,000 (85.0%) | `exchange` vs `baseline` | +5.45 pp | [+4.17, +6.73] pp | [-6.59, +17.49] pp | Normal only: first |
| 4 | rational | `exchange` 1,501/4,000 (37.5%) | `exchange` vs `baseline` | +1.65 pp | [+0.22, +3.08] pp | [-10.39, +13.69] pp | Normal only: first |
| 4 | learning | `search_08` 1,449/4,000 (36.2%) | `exchange` vs `baseline` | +1.73 pp | [+0.20, +3.25] pp | [-10.31, +13.76] pp | Normal only: first; leader outside pair |
| 4 | random | `search_08` 2,240/4,000 (56.0%) | `exchange` vs `search_08` | -3.70 pp | [-7.01, -0.39] pp | [-15.74, +8.34] pp | Normal only: second |
| 4 | mixed | `exchange` 1,538/4,000 (38.5%) | `exchange` vs `search_21` | +1.57 pp | [-1.23, +4.38] pp | [-10.46, +13.61] pp | Unresolved |
| 5 | honest | `bluff_heavy` 1,949/5,000 (39.0%) | `bluff_heavy` vs `block_aggressive` | +10.06 pp | [+7.71, +12.41] pp | [-1.98, +22.10] pp | Normal only: first |
| 5 | bluffing | `challenge_heavy` 1,287/5,000 (25.7%) | `challenge_heavy` vs `card_bold` | +5.46 pp | [+2.49, +8.43] pp | [-6.58, +17.50] pp | Normal only: first |
| 5 | skeptical | `exchange` 4,214/5,000 (84.3%) | `exchange` vs `baseline` | +5.78 pp | [+4.65, +6.91] pp | [-6.26, +17.82] pp | Normal only: first |
| 5 | rational | `exchange` 1,428/5,000 (28.6%) | `exchange` vs `baseline` | +1.24 pp | [-0.03, +2.51] pp | [-10.80, +13.28] pp | Unresolved |
| 5 | learning | `search_08` 1,450/5,000 (29.0%) | `search_08` vs `exchange` | +0.34 pp | [-1.99, +2.67] pp | [-11.70, +12.38] pp | Unresolved |
| 5 | random | `exchange` 2,554/5,000 (51.1%) | `assassin` vs `exchange` | -0.86 pp | [-3.98, +2.26] pp | [-12.90, +11.18] pp | Unresolved |
| 5 | mixed | `exchange` 1,706/5,000 (34.1%) | `search_21` vs `exchange` | -1.34 pp | [-3.75, +1.07] pp | [-13.38, +10.70] pp | Unresolved |
| 6 | honest | `search_00` 1,123/6,000 (18.7%) | `search_00` vs `card_cautious` | +0.08 pp | [-0.61, +0.77] pp | [-11.95, +12.12] pp | Unresolved |
| 6 | bluffing | `search_21` 1,190/6,000 (19.8%) | `search_21` vs `search_12` | +1.17 pp | [+0.16, +2.17] pp | [-10.87, +13.20] pp | Normal only: first |
| 6 | skeptical | `exchange` 5,039/6,000 (84.0%) | `exchange` vs `baseline` | +5.33 pp | [+4.30, +6.37] pp | [-6.70, +17.37] pp | Normal only: first |
| 6 | rational | `exchange` 1,794/6,000 (29.9%) | `exchange` vs `baseline` | +1.75 pp | [+0.56, +2.94] pp | [-10.29, +13.79] pp | Normal only: first |
| 6 | learning | `exchange` 1,915/6,000 (31.9%) | `exchange` vs `baseline` | +2.32 pp | [+1.09, +3.54] pp | [-9.72, +14.35] pp | Normal only: first |
| 6 | random | `foreign_aid` 3,631/6,000 (60.5%) | `foreign_aid` vs `exchange` | +0.48 pp | [-2.08, +3.05] pp | [-11.55, +12.52] pp | Unresolved |
| 6 | mixed | `exchange` 2,046/6,000 (34.1%) | `exchange` vs `baseline` | +2.05 pp | [+0.78, +3.32] pp | [-9.99, +14.09] pp | Normal only: first |

Five conservative family bounds favor the first preselected policy, and none favor the second. Twenty-six approximate normal bounds favor the first and one favors the second; eight normal pair comparisons remain unresolved. The conservative half-width is about 12.04 percentage points at 1,000 blocks for this 35-comparison family. Four of its five positive lower bounds clear the predeclared +2-point practical threshold. The two-player rational-field bound starts at +1.31 points, so its direction is supported without clearing that threshold under the conservative method.

The single approximate-normal reversal is four-player random: the screening-selected second policy, `search_08`, led `exchange` by 3.70 points in confirmation. The conservative interval includes zero. In four-player learning, `search_08` was the observed leader at 1,449/4,000, just six wins ahead of `exchange`; it was **outside** the screening-selected `exchange` versus `baseline` pair. That pair’s positive normal interval cannot be used to claim superiority for `search_08`.

## Broad performance across seven fields

Equal-field averages give each of the seven opponent fields the same weight within a player count. The sensitivity scenario doubles the rational and learning weights. The table’s rankings and worst-field rates are **descriptive post-confirmation summaries**; the 35 paired intervals above do not cover every ranking or worst-field selection.

| Players | Equal-field leader | Mean | Equal-field runner-up | Doubled rational/learning leader | Scenario mean | Leader’s weakest field |
| ---: | --- | ---: | --- | --- | ---: | --- |
| 2 | `bluff_heavy` | 66.74% | `taxer` (60.74%) | `bluff_heavy` | 69.69% | skeptical: 20.95% |
| 3 | `bluff_heavy` | 49.15% | `search_08` (46.53%) | `bluff_heavy` | 51.54% | skeptical: 12.47% |
| 4 | `exchange` | 41.66% | `search_21` (40.97%) | `exchange` | 40.58% | bluffing: 17.82% |
| 5 | `exchange` | 37.01% | `search_21` (35.04%) | `exchange` | 35.14% | bluffing: 12.76% |
| 6 | `exchange` | 38.65% | `baseline` (36.68%) | `exchange` | 36.93% | bluffing: 14.57% |

The leader stays the same under the second weighting: `bluff_heavy` at two and three players, `exchange` at four through six. That stability is conditional on these two artificial field weightings. The weak side matters: `bluff_heavy` won only 20.95% and 12.47% against skeptical opponents at two and three players, while `exchange` fell to 17.82%, 12.76%, and 14.57% against bluffing opponents at four, five, and six players. None is a safe universal prescription.

## Targeted counters

Screening selected `exchange` and `card_cautious` as targets, then a separate search selected `bluff_heavy` against copies of each target. The following **fresh-seed** confirmation compares `bluff_heavy` with a target-policy self-play control. Every contrast uses 1,000 complete rotation blocks and a separate four-comparison simultaneous family. The paired difference is counter minus target control. The theoretical `1 / players` reference stays fixed; the observed target self-play rate can be lower when games draw.

| Players | Target population | Counter wins | Target-control wins | Paired lead | Normal 95% | Conservative 95% |
| ---: | --- | ---: | ---: | ---: | --- | --- |
| 2 | `card_cautious` copies | 1,627/2,000 (81.35%) | 986/2,000 (49.30%) | +32.05 pp | [+30.04, +34.06] pp | [+21.98, +42.12] pp |
| 2 | `exchange` copies | 1,629/2,000 (81.45%) | 1,000/2,000 (50.00%) | +31.45 pp | [+29.54, +33.36] pp | [+21.38, +41.52] pp |
| 4 | `card_cautious` copies | 1,717/4,000 (42.93%) | 999/4,000 (24.98%) | +17.95 pp | [+15.92, +19.98] pp | [+7.88, +28.02] pp |
| 4 | `exchange` copies | 1,964/4,000 (49.10%) | 1,000/4,000 (25.00%) | +24.10 pp | [+21.84, +26.36] pp | [+14.03, +34.17] pp |

All four conservative bounds exclude zero and clear the +2-point practical threshold. These are strong **targeted** effects in the specified two- and four-player matchups. They do not mean habitual Tax bluffing is broadly best: the same `bluff_heavy` policy fares poorly against skeptical opponents in the seven-field confirmation. The two-player `card_cautious` self-play control has 28 draws in 2,000 games, which is why its observed control win rate is 49.30% rather than 50%.

## What the ablations say

Each ablation changes a defined part of `public_learning`. The paired difference below is full `public_learning` minus its modified version. There are 56 frozen comparisons: four modifications, two player counts, seven fields, and 500 rotation blocks per cell. The normal and conservative bounds each adjust over all 56 comparisons. These are local tests of this policy implementation, not general estimates of the value of information, memory, targeting, or card keeping.

| Removed or changed component | Observed paired range across 14 cells | Normal bounds excluding zero | Conservative bounds excluding zero |
| --- | ---: | ---: | ---: |
| `ablate_no_claim_cards` | -13.50 to +6.20 pp | 1 favor full; 4 favor ablation | 0 favor full; 0 favor ablation |
| `ablate_no_history` | -1.40 to +18.85 pp | 2 favor full; 1 favor ablation | 1 favor full; 0 favor ablation |
| `ablate_random_target` | -11.95 to +1.35 pp | 0 favor full; 5 favor ablation | 0 favor full; 0 favor ablation |
| `ablate_fixed_retention` | -2.10 to +0.30 pp | 0 favor full; 1 favor ablation | 0 favor full; 0 favor ablation |

The one conservative-supported ablation is four-player skeptical play: full `public_learning` beat `ablate_no_history` by +18.85 points, with normal [+15.81, +21.89] and conservative [+1.28, +36.42] point intervals. Its conservative lower bound is +1.28 points, so it supports a positive effect in that cell but not a guaranteed +2-point practical effect. Other history cells do not justify a broad learning advantage. The history toggle removes both public proof-record learning and table-wide challenge-pressure adjustment.

The claim-card ablation can outperform the full version against honest opponents and underperform it against frequent bluffers; none of its conservative intervals excludes zero. At two players, `ablate_random_target` has exactly the same outcomes as the full policy because there is only one live opponent to target. At four players, random targeting sometimes wins more often than the full threat heuristic under approximate normal bounds, but no conservative interval separates them. Fixed retention produces small, inconsistent effects. `ablate_no_claim_cards` changes claim credibility and impossible-claim challenges, while card availability still enters action and target scores; `ablate_fixed_retention` changes both Exchange keeps and influence discard. These scopes limit a simple causal reading.

## Six-player stress panel

Ten named policies were separately tested in six-player self-play and five heterogeneous fields, with 100 complete rotation blocks or 600 games per policy/field. Assault cycles `eliminator`, `assassin`, and `bluff_heavy`; economy cycles `taxer`, `captain`, and `exchange_builder`; chaos cycles `public_random`, `block_aggressive`, and `challenge_heavy`; alternating cycles `card_cautious`, `card_bold`, and `public_learning`; mixed cycles the seven primary-field types. The table gives **wins out of 600 (win rate)**. There are no prespecified pair tests or simultaneous intervals for this panel, so its ranks are descriptive.

| Candidate | Assault | Economy | Chaos | Alternating | Mixed |
| --- | ---: | ---: | ---: | ---: | ---: |
| `baseline` | 136/600 (22.7%) | 171/600 (28.5%) | 283/600 (47.2%) | 185/600 (30.8%) | 213/600 (35.5%) |
| `card_cautious` | 130/600 (21.7%) | 138/600 (23.0%) | 266/600 (44.3%) | 131/600 (21.8%) | 158/600 (26.3%) |
| `defensive` | 129/600 (21.5%) | 97/600 (16.2%) | 217/600 (36.2%) | 113/600 (18.8%) | 131/600 (21.8%) |
| `exchange_builder` | 96/600 (16.0%) | 93/600 (15.5%) | 200/600 (33.3%) | 112/600 (18.7%) | 135/600 (22.5%) |
| `card_balanced` | 96/600 (16.0%) | 89/600 (14.8%) | 184/600 (30.7%) | 118/600 (19.7%) | 112/600 (18.7%) |
| `public_learning` | 87/600 (14.5%) | 78/600 (13.0%) | 173/600 (28.8%) | 106/600 (17.7%) | 101/600 (16.8%) |
| `bluff_heavy` | 105/600 (17.5%) | 111/600 (18.5%) | 92/600 (15.3%) | 103/600 (17.2%) | 98/600 (16.3%) |
| `eliminator` | 90/600 (15.0%) | 83/600 (13.8%) | 147/600 (24.5%) | 93/600 (15.5%) | 94/600 (15.7%) |
| `card_bold` | 88/600 (14.7%) | 49/600 (8.2%) | 66/600 (11.0%) | 45/600 (7.5%) | 59/600 (9.8%) |
| `challenge_heavy` | 10/600 (1.7%) | 9/600 (1.5%) | 14/600 (2.3%) | 0/600 (0.0%) | 1/600 (0.2%) |

The `baseline` control had the highest observed rate among these ten policies in all five heterogeneous stress fields. Every policy won exactly 100/600 (16.67%) in its own six-player self-play; that self-play symmetry is a seat-balance diagnostic, not a strength ranking. This panel had 67 capped draws in 36,000 games (0.186%). Crucially, `exchange` and the numbered search finalists were **not** in the stress candidate set, so this result does not compare `baseline` with the confirmation panel’s broad leaders.

## How to use these policies

- Against players modeled as rarely challenging false claims, `bluff_heavy` is a high-performing tested exploit at two through five players. It claims Tax on non-Coup turns and attempts every available block; its skeptical-field collapse makes the exploit fragile when the table starts challenging.
- Against a table modeled as frequent bluffers, `challenge_heavy` has conservative-supported leads at two and three players. It challenges every role claim and performs poorly in several other fields and six-player stress settings. The contrast suggests challenge pressure should depend on opponent behavior.
- Against indiscriminate challengers, the `exchange` control has the highest observed rate at every player count. It is mostly the truthful baseline with occasional held-Ambassador Exchange, so these data do not isolate Exchange itself as the cause. Its pairwise lead over baseline has approximate normal support but no conservative separation at any player count.
- For an unspecified mix of these seven bot fields, the equal-field summary favors `bluff_heavy` at two and three players and `exchange` at four through six. These are scenario rankings without a population-sampling guarantee. If the real table differs from the seven fields, the recommendation can reverse.

The numbered variants should be read by their [frozen configurations](../research_results/2026-10-12-v2/plan.json), not their IDs alone. `search_08` uses high bluff and block-bluff propensity parameters, favors rich targets, and sometimes seeks Exchange; its 0.60 bluff parameter is not an observed 60% bluff frequency. `search_21` uses public history, a stronger challenge multiplier, rich-target selection, and a zero action-bluff propensity parameter. `search_00` avoids action and block bluffs and had a very small, unresolved six-player honest-field lead. These hand-scored policies are not solved game-theoretic strategies.

## Limits and reproducibility

The normal simultaneous intervals are approximate; the Hoeffding bounds are conservative under the independent seed-block sampling model. Pseudorandom seed panels and complete rotations make the simulation reproducible, but the intervals describe its programmed matchup distribution, not uncertainty about real human tables. Observed leaders were selected after seeing the 16-policy confirmation union; only the 35 **earlier selected** pairs get the stated primary family comparison. The counter and ablation analyses have their own separate frozen four- and 56-comparison families. The pooled and stress rankings do not inherit those intervals.

The game omits persuasion, deals, team play, expansion roles, and human adaptation. Advanced policies use a card-availability prior and hand-chosen action values, not calibrated win-probability optimization. Public behavior can change after a policy is recognized. Draws come from the 1,000-turn cap. Mechanism counters are preserved and internally reconciled, but the raw outcome CSV does not contain every action event, so mechanism patterns are descriptive rather than independently replayed from those rows.

For review or reproduction, see the [research design](RESEARCH_DESIGN.md), [strategy implementation review](STRATEGY_REVIEW.md), [analysis code](../analyze_strategy_research.py), [stage summaries and raw outcomes](../research_results/2026-10-12-v2/), and [replay-audit method](REPLAY_AUDIT.md). The source files are fingerprinted by SHA-256 in the plan and replay receipt; the frozen execution checkout is revision `12ab9e1`. The analysis verifier reconciles the saved findings and stage summaries to the archived raw panels and refuses stale saved findings.
