# Coup rules and strategy findings

Research snapshot: 10 October 2026. These findings apply to the standard base deck and the programmed policies in this repository.

## Rulebook findings that changed the simulator

The original eight-page [Coup rulebook](https://www.qugs.org/rules/r131357.pdf) specifies three copies of each of five roles, two influence cards per player, two starting coins, and a Coup requirement when a turn begins at 10 or more coins. Its two-player base rule gives the starting player one coin. A challenged **truthful** action continues after the challenger loses an influence and the claimant replaces the shown card. A challenged **truthful** counteraction still blocks; a disproved counteraction fails. The actor and other opponents may challenge a block. Either Captain or Ambassador may block Steal. Exchange draws two cards and returns two, even when the player has only one remaining influence.

An Assassin pays three coins before the claim resolves. If its claim is successfully challenged, the action fails and the fee is returned to a surviving actor. If Contessa successfully blocks, the fee stays spent. A target that loses a challenge to a truthful Assassin claim can lose another influence to the ensuing assassination. These rules have focused tests in [test_coup_simulator.py](test_coup_simulator.py).

The booklet says an eliminated player's coins return to the Treasury. One printed example appears to award a steal after the target is eliminated by a false block challenge; this engine follows the general elimination rule and therefore cannot steal coins from an eliminated target. The publisher-maintained [Dized Coup rules](https://rules.dized.com/game/xzsTtI3VTV-2wvos3otxIg/coup) provide a second reference.

## Confirmed four-player comparison

Each policy below played **6,000 games per opponent field**, evenly across the four seats. The runner used a separate seed panel from screening. “Leader” means highest observed win rate among the seven confirmed finalists, not a universal best strategy. All rates divide wins by all scheduled games; draws remain in the denominator.

| Opponent field | Observed leader | Wins | Win rate | Runner-up | Runner-up rate | Paired lead, simultaneous 95% interval |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| Honest baseline | Bluff heavy | 3,485 / 6,000 | 58.1% | Block aggressive | 44.7% | +13.4 points [11.9, 14.9] |
| Bluff heavy | Challenge heavy | 2,558 / 6,000 | 42.6% | Bluff heavy | 25.5% | +17.1 points [15.0, 19.2] |
| Challenge heavy | Exchange | 4,999 / 6,000 | 83.3% | Baseline | 78.7% | +4.7 points [3.9, 5.4] |
| Mixed | Exchange | 1,786 / 6,000 | 29.8% | Block aggressive | 27.9% | +1.9 points [0.5, 3.3] |

“Honest baseline” opponents make only held-card action claims; “Bluff heavy” opponents claim Tax and blocks whether or not they hold the role; “Challenge heavy” opponents challenge every role claim. In the mixed field, opponent policies cycle through baseline, bluff heavy, and challenge heavy, varying their order by game index. The mixed lead is comparatively small. The screening panel had placed Block aggressive first in that field, illustrating why the separate confirmation mattered.

The screening panel selected a top-two pair for each field before confirmation. Those same pairs remained the top two in confirmation, although their order reversed in the mixed field. The intervals above compare each preselected pair on matched seed and seat panels. They are simultaneous 95% paired normal intervals across the four field comparisons, using a Bonferroni correction and 6,000 observations per field. They exclude zero for these four comparisons. They do not establish that the winner would beat every untested policy, human player, or different opponent mix. The table's individual win-rate intervals in the CSV and website are Wilson intervals and should not be read as a pairwise test.

The matchups suggest a useful practical pattern within this model: unchecked bluffing exploits trusting opponents, aggressive challenges punish frequent bluffs, and truthful claims become valuable against opponents that challenge indiscriminately. That mechanism is an inference from the policy definitions and matchups, not a causal isolation experiment.

## Wider screening

The screening panel ran **88,000 games** across 2–6 players, eleven candidates, and four fields, with 100 games per seat. Nine games reached the 1,000-action cap. The four-player screening selected the top three candidates in each field plus baseline, producing the seven-policy confirmation union in [confirmation_plan.json](confirmation_plan.json). The confirmation panel ran **168,000 games** and had 17 capped draws.

The 2–6-player rates, per-seat rows, and individual outcomes remain in [results.csv](results.csv), [benchmark_results.csv](benchmark_results.csv), and [games.csv](games.csv). They are exploratory. Compare rows only within one player count and one opponent field. The two-player setup is asymmetric because seat zero starts with one coin; all players took every seat equally often.

## Policy definitions

All supplied policies choose to Coup at seven coins even though the rule only mandates one at ten. They share a public-state target heuristic, a simple influence-loss preference, truthful blocks when holding a block role, automatic proof when holding a challenged role, and a one-turn Income fallback after two failed actions.

| Policy | Distinct action or response rule |
| --- | --- |
| Baseline | Truthful Tax with Duke; truthful Steal with Captain; occasional truthful Exchange with Ambassador; otherwise Foreign Aid. Challenges impossible claims only. |
| Income | Guaranteed Income until Coup. |
| Foreign Aid | Attempts Foreign Aid until Coup. |
| Taxer | Claims Duke Tax every non-Coup turn, including when bluffing. |
| Captain | Claims Steal when opponents have coins, including when bluffing; otherwise Foreign Aid. |
| Assassin | Claims Assassinate once it has at least three coins; otherwise Foreign Aid. |
| Exchange | Sometimes exchanges with a held Ambassador when it lacks Duke; otherwise follows baseline. |
| Bluff heavy | Claims Tax on each non-Coup turn and claims every available block. |
| Challenge low | Baseline actions plus a 15% challenge chance for Assassin, Captain, or Contessa claims. |
| Challenge heavy | Baseline actions, challenges every role claim. |
| Block aggressive | Baseline actions, claims every available block. |

A challenge based on all three copies of a role being accounted for in private own cards plus public revealed cards is always made by every policy. A block is attempted truthfully by default, including an Ambassador block of Steal. The engine resolves simultaneous response opportunities clockwise as a documented convention.

## Limits and next research steps

The engine does not represent persuasion, table talk, binding deals, team play, expansion roles, or the optional two-player card setup. It always proves a held claimed card when challenged, uses one target-selection rule, and optimizes Exchange keeps with a fixed role ranking. It does not model a finite Treasury supply. The 1,000-action cap can produce draws from policy loops; these are counted explicitly.

The current study compares understandable fixed heuristics. A stronger search would parameterize claim frequency, challenge thresholds using public history, target choice, and exchange value, then tune on one seed panel and confirm on another. Head-to-head counter experiments and robustness against opponent populations beyond the four fields would be needed before claiming a broadly strongest policy.
