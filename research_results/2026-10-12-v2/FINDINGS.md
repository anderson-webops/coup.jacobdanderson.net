# Coup strategy research findings

These results compare a finite, frozen policy population under the stated Coup rules and opponent fields. They do not establish an unrestricted optimal strategy or predict human play.

## Verified study size

| Stage | Games | Draws | Jobs |
| --- | ---: | ---: | ---: |
| tuning | 64,512 | 0 | 504 |
| screening | 336,000 | 8 | 840 |
| confirmation | 2,240,000 | 78 | 560 |
| counter_search | 9,216 | 9 | 96 |
| counters | 24,000 | 33 | 8 |
| ablations | 105,000 | 0 | 70 |
| stress | 36,000 | 67 | 60 |

## Frozen confirmation pairs

The first and second candidates in each row were selected before confirmation. A positive difference favors the first. The normal family interval is approximate; the Hoeffding family interval is conservative.

| Players | Field | Preselected first | Preselected second | Difference | Normal family 95% | Conservative family 95% |
| ---: | --- | --- | --- | ---: | --- | --- |
| 2 | bluffing | challenge_heavy | card_bold | +14.8% | [+10.9%, +18.8%] | [+2.8%, +26.9%] |
| 2 | honest | bluff_heavy | block_aggressive | +9.4% | [+6.8%, +12.1%] | [-2.6%, +21.5%] |
| 2 | learning | bluff_heavy | taxer | +7.6% | [+5.7%, +9.6%] | [-4.4%, +19.7%] |
| 2 | mixed | bluff_heavy | challenge_heavy | +7.5% | [+3.0%, +12.0%] | [-4.5%, +19.5%] |
| 2 | random | bluff_heavy | taxer | +2.9% | [+0.6%, +5.3%] | [-9.1%, +15.0%] |
| 2 | rational | bluff_heavy | exchange | +13.4% | [+9.8%, +16.9%] | [+1.3%, +25.4%] |
| 2 | skeptical | exchange | baseline | +7.3% | [+5.4%, +9.2%] | [-4.7%, +19.3%] |
| 3 | bluffing | challenge_heavy | search_08 | +26.0% | [+22.1%, +29.9%] | [+14.0%, +38.0%] |
| 3 | honest | bluff_heavy | taxer | +16.4% | [+14.1%, +18.7%] | [+4.4%, +28.5%] |
| 3 | learning | bluff_heavy | taxer | +3.3% | [+2.1%, +4.5%] | [-8.8%, +15.3%] |
| 3 | mixed | bluff_heavy | exchange | -0.9% | [-5.1%, +3.3%] | [-12.9%, +11.1%] |
| 3 | random | search_08 | bluff_heavy | +3.5% | [+0.1%, +6.9%] | [-8.5%, +15.5%] |
| 3 | rational | bluff_heavy | taxer | +3.4% | [+2.0%, +4.8%] | [-8.6%, +15.4%] |
| 3 | skeptical | exchange | baseline | +6.2% | [+4.7%, +7.7%] | [-5.8%, +18.2%] |
| 4 | bluffing | search_08 | challenge_heavy | +6.6% | [+3.2%, +9.9%] | [-5.5%, +18.6%] |
| 4 | honest | bluff_heavy | block_aggressive | +15.8% | [+12.9%, +18.7%] | [+3.8%, +27.8%] |
| 4 | learning | exchange | baseline | +1.7% | [+0.2%, +3.3%] | [-10.3%, +13.8%] |
| 4 | mixed | exchange | search_21 | +1.6% | [-1.2%, +4.4%] | [-10.5%, +13.6%] |
| 4 | random | exchange | search_08 | -3.7% | [-7.0%, -0.4%] | [-15.7%, +8.3%] |
| 4 | rational | exchange | baseline | +1.7% | [+0.2%, +3.1%] | [-10.4%, +13.7%] |
| 4 | skeptical | exchange | baseline | +5.5% | [+4.2%, +6.7%] | [-6.6%, +17.5%] |
| 5 | bluffing | challenge_heavy | card_bold | +5.5% | [+2.5%, +8.4%] | [-6.6%, +17.5%] |
| 5 | honest | bluff_heavy | block_aggressive | +10.1% | [+7.7%, +12.4%] | [-2.0%, +22.1%] |
| 5 | learning | search_08 | exchange | +0.3% | [-2.0%, +2.7%] | [-11.7%, +12.4%] |
| 5 | mixed | search_21 | exchange | -1.3% | [-3.8%, +1.1%] | [-13.4%, +10.7%] |
| 5 | random | assassin | exchange | -0.9% | [-4.0%, +2.3%] | [-12.9%, +11.2%] |
| 5 | rational | exchange | baseline | +1.2% | [-0.0%, +2.5%] | [-10.8%, +13.3%] |
| 5 | skeptical | exchange | baseline | +5.8% | [+4.6%, +6.9%] | [-6.3%, +17.8%] |
| 6 | bluffing | search_21 | search_12 | +1.2% | [+0.2%, +2.2%] | [-10.9%, +13.2%] |
| 6 | honest | search_00 | card_cautious | +0.1% | [-0.6%, +0.8%] | [-12.0%, +12.1%] |
| 6 | learning | exchange | baseline | +2.3% | [+1.1%, +3.5%] | [-9.7%, +14.4%] |
| 6 | mixed | exchange | baseline | +2.0% | [+0.8%, +3.3%] | [-10.0%, +14.1%] |
| 6 | random | foreign_aid | exchange | +0.5% | [-2.1%, +3.1%] | [-11.6%, +12.5%] |
| 6 | rational | exchange | baseline | +1.7% | [+0.6%, +2.9%] | [-10.3%, +13.8%] |
| 6 | skeptical | exchange | baseline | +5.3% | [+4.3%, +6.4%] | [-6.7%, +17.4%] |

## Observed leaders

These are point-estimate rankings across the frozen union. The pairwise intervals above do not establish a winner over every union member.

| Players | Field | Highest observed | Win rate |
| ---: | --- | --- | ---: |
| 2 | bluffing | challenge_heavy | 79.2% |
| 2 | honest | bluff_heavy | 81.9% |
| 2 | learning | bluff_heavy | 79.2% |
| 2 | mixed | bluff_heavy | 65.7% |
| 2 | random | bluff_heavy | 88.6% |
| 2 | rational | bluff_heavy | 80.8% |
| 2 | skeptical | exchange | 82.2% |
| 3 | bluffing | challenge_heavy | 61.5% |
| 3 | honest | bluff_heavy | 70.8% |
| 3 | learning | bluff_heavy | 59.0% |
| 3 | mixed | exchange | 45.3% |
| 3 | random | search_08 | 66.8% |
| 3 | rational | bluff_heavy | 60.8% |
| 3 | skeptical | exchange | 85.7% |
| 4 | bluffing | search_08 | 48.8% |
| 4 | honest | bluff_heavy | 58.6% |
| 4 | learning | search_08 | 36.2% |
| 4 | mixed | exchange | 38.5% |
| 4 | random | search_08 | 56.0% |
| 4 | rational | exchange | 37.5% |
| 4 | skeptical | exchange | 85.0% |
| 5 | bluffing | challenge_heavy | 25.7% |
| 5 | honest | bluff_heavy | 39.0% |
| 5 | learning | search_08 | 29.0% |
| 5 | mixed | exchange | 34.1% |
| 5 | random | exchange | 51.1% |
| 5 | rational | exchange | 28.6% |
| 5 | skeptical | exchange | 84.3% |
| 6 | bluffing | search_21 | 19.8% |
| 6 | honest | search_00 | 18.7% |
| 6 | learning | exchange | 31.9% |
| 6 | mixed | exchange | 34.1% |
| 6 | random | foreign_aid | 60.5% |
| 6 | rational | exchange | 29.9% |
| 6 | skeptical | exchange | 84.0% |

## Counter and ablation checks

Counter targets and ablation components were frozen in their stage plans. Their intervals form separate comparison families. The complete values are in findings.json.

## Limits

- Only the finite frozen policy population and seven programmed opponent fields were tested.
- Observed leaders, pooled rates, and worst-field rankings are descriptive post-confirmation comparisons; the simultaneous paired intervals cover the 35 preselected pairs only.
- The normal family intervals are approximate. The Hoeffding family intervals are conservative under independent rotation blocks and may leave small differences unresolved.
- All games use the programmed standard base-game rules, response order, public-information model, and 1000-turn cap; human opponents may behave differently.
- Two-player starting coins are asymmetric; compare two-player results separately from larger tables.
- Counter and ablation checks have their own frozen families and do not prove a policy is universally optimal.
