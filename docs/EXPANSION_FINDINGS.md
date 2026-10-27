# Coup expansion strategy findings

The frozen expansion study contains **1,908,576 scheduled games** across three rules options and two through ten players. Its **17,960 capped games (0.94%)** remain in every win-rate denominator.

## Strategy recommendations

- Tax bluffer led the equal-field averages at two and three players in all three rules options. Its weakness was the Always challenge field; those broad leads are not a recommendation to bluff into frequent challenges.
- Defensive conversion led at every four-through-ten-player setting with allegiances, whether Ambassador or Inquisitor was used. This compares complete policies, not the isolated value of conversion.
- Inquisitor-only results varied more: Truthful economy and Defensive conversion tied at five players; the two finalists were close again at nine. A policy called Defensive conversion performs no conversion when allegiances are absent. Its other decision settings still differ.

## Observed broad leaders

Each row ranks only the **two screening-selected finalists** confirmed at that rules option and player count. Five programmed opponent fields receive equal weight. These are descriptive averages, not simultaneous tests of an overall winner, and they do not measure human opponent frequencies. Wins and games in a tied row apply to each tied policy.

### Inquisitor only

| Players | Observed leader among two finalists | Wins / games | Equal-field win rate | Weakest field |
| ---: | --- | ---: | ---: | --- |
| 2 | Tax bluffer | 6,609 / 10,000 | 66.09% | Always challenge (19.55%) |
| 3 | Tax bluffer | 7,500 / 15,000 | 50.00% | Always challenge (16.73%) |
| 4 | Tax bluffer | 7,987 / 20,000 | 39.93% | Always challenge (14.07%) |
| 5 | Truthful economy = Defensive conversion | 8,093 / 25,000 | 32.37% | Truthful economy: Truthful (17.96%); Defensive conversion: Balanced (19.82%) |
| 6 | Truthful economy | 10,902 / 30,000 | 36.34% | Truthful (16.50%) |
| 7 | Truthful economy | 10,027 / 35,000 | 28.65% | Truthful (12.54%) |
| 8 | Truthful economy | 12,648 / 40,000 | 31.62% | Truthful (11.61%) |
| 9 | Defensive conversion | 11,902 / 45,000 | 26.45% | Mixed (9.86%) |
| 10 | Truthful economy | 14,223 / 50,000 | 28.45% | Truthful (9.18%) |

### Allegiances + Ambassador

| Players | Observed leader among two finalists | Wins / games | Equal-field win rate | Weakest field |
| ---: | --- | ---: | ---: | --- |
| 2 | Tax bluffer | 6,555 / 10,000 | 65.55% | Always challenge (18.75%) |
| 3 | Tax bluffer | 7,052 / 15,000 | 47.01% | Always challenge (14.27%) |
| 4 | Defensive conversion | 8,067 / 20,000 | 40.34% | Tax bluffers (22.18%) |
| 5 | Defensive conversion | 9,137 / 25,000 | 36.55% | Tax bluffers (24.82%) |
| 6 | Defensive conversion | 10,746 / 30,000 | 35.82% | Truthful (18.17%) |
| 7 | Defensive conversion | 10,491 / 35,000 | 29.97% | Tax bluffers (15.79%) |
| 8 | Defensive conversion | 12,533 / 40,000 | 31.33% | Truthful (15.82%) |
| 9 | Defensive conversion | 12,287 / 45,000 | 27.30% | Mixed (12.50%) |
| 10 | Defensive conversion | 13,870 / 50,000 | 27.74% | Truthful (12.18%) |

### Allegiances + Inquisitor

| Players | Observed leader among two finalists | Wins / games | Equal-field win rate | Weakest field |
| ---: | --- | ---: | ---: | --- |
| 2 | Tax bluffer | 6,619 / 10,000 | 66.19% | Always challenge (18.90%) |
| 3 | Tax bluffer | 7,238 / 15,000 | 48.25% | Always challenge (16.17%) |
| 4 | Defensive conversion | 8,291 / 20,000 | 41.45% | Tax bluffers (21.48%) |
| 5 | Defensive conversion | 9,483 / 25,000 | 37.93% | Tax bluffers (24.02%) |
| 6 | Defensive conversion | 10,960 / 30,000 | 36.53% | Truthful (21.15%) |
| 7 | Defensive conversion | 10,737 / 35,000 | 30.68% | Tax bluffers (15.10%) |
| 8 | Defensive conversion | 12,643 / 40,000 | 31.61% | Mixed (17.20%) |
| 9 | Defensive conversion | 12,545 / 45,000 | 27.88% | Mixed (12.08%) |
| 10 | Defensive conversion | 13,817 / 50,000 | 27.63% | Mixed (12.33%) |

At nine-player Inquisitor-only tables, Defensive conversion's average lead over Truthful economy was just 0.17 percentage points. At three-player Allegiances + Inquisitor tables, Tax bluffer's lead over Defensive conversion was 0.70 points. Neither descriptive average supplies a paired overall confidence bound.

## Supported and unresolved differences

The predeclared family contains **135 field-specific paired comparisons**. Approximate normal simultaneous intervals exclude zero in **116** cases; conservative simultaneous Hoeffding bounds exclude zero in **45**. Thus **71** have approximate support only, and **19** remain unresolved under both methods. Conservative bounds leave **90** unresolved.

| Rules option | Comparisons | Approximate: exclude zero | Approximate: practical | Conservative: exclude zero | Conservative: practical |
| --- | ---: | ---: | ---: | ---: | ---: |
| Inquisitor only | 45 | 35 | 27 | 18 | 17 |
| Allegiances + Ambassador | 45 | 40 | 32 | 12 | 11 |
| Allegiances + Inquisitor | 45 | 41 | 32 | 15 | 12 |
| Total | 135 | 116 | 91 | 45 | 40 |

Counts include supported advantages in either direction. Practical support requires the entire interval beyond two percentage points in that direction. All three rows are subsets of the same 135-comparison adjustment, not separate smaller families.

The following conditional contrasts illustrate why the opponent field matters. Each is a predeclared finalist comparison, oriented toward the higher observed rate. Their conservative lower bounds also exceed the practical threshold.

| Rules option | Players | Opponents | Favored policy vs rival | Win rates | Difference | Conservative 95% simultaneous bounds |
| --- | ---: | --- | --- | ---: | ---: | --- |
| Inquisitor only | 7 | Always challenge | Truthful economy vs Tax bluffer | 86.17% vs 8.64% | +77.53 pp | +64.42 to +90.64 pp |
| Allegiances + Ambassador | 4 | Always challenge | Defensive conversion vs Tax bluffer | 74.78% vs 12.80% | +61.98 pp | +48.86 to +75.09 pp |
| Allegiances + Inquisitor | 4 | Always challenge | Defensive conversion vs Tax bluffer | 78.20% vs 13.15% | +65.05 pp | +51.94 to +78.16 pp |

## Fresh targeted counters

Targets were fixed from screening, counters selected on separate search games, and both then measured on fresh matched blocks. The reference is the target playing against copies of itself. A counter target can differ from the eventual confirmation leader.

| Rules option | Players | Counter vs target | Counter wins / games | Counter rate | Target control | Difference | Conservative bounds | Finding |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| Inquisitor only | 2 | Always challenge vs Tax bluffer | 1,644 / 2,000 | 82.20% | 50.00% | +32.20 pp | +21.73 to +42.67 pp | Practical counter supported |
| Inquisitor only | 6 | Tax bluffer vs Truthful economy | 1,315 / 6,000 | 21.92% | 15.68% | +6.23 pp | -4.24 to +16.70 pp | Approximate support only |
| Allegiances + Ambassador | 4 | Tax bluffer vs Defensive conversion | 1,502 / 4,000 | 37.55% | 23.85% | +13.70 pp | +3.23 to +24.17 pp | Practical counter supported |
| Allegiances + Ambassador | 10 | Tax bluffer vs Defensive conversion | 1,372 / 10,000 | 13.72% | 10.42% | +3.30 pp | -7.17 to +13.77 pp | Approximate support only |
| Allegiances + Inquisitor | 4 | Always challenge vs Tax bluffer | 1,650 / 4,000 | 41.25% | 25.00% | +16.25 pp | +5.78 to +26.72 pp | Practical counter supported |
| Allegiances + Inquisitor | 10 | Tax bluffer vs Defensive conversion | 2,015 / 10,000 | 20.15% | 9.81% | +10.34 pp | -0.13 to +20.81 pp | Approximate support only |

Three counters have conservative practical support: Always challenge against Tax bluffer in two-player Inquisitor-only games, Tax bluffer against Defensive conversion in four-player Allegiances + Ambassador games, and Always challenge against Tax bluffer in four-player Allegiances + Inquisitor games. The other three have approximate practical support but remain unresolved under conservative bounds. All six belong to one six-comparison family.

A high equal-field average therefore does not make a policy safe against a population designed to exploit it. These counter results concern copies of the named target; they do not establish performance against a diverse human table.

## Capped games

Games without a winner after 1,000 actions count as draws. The distribution is uneven:

| Rules option | Screening | Confirmation | Counter search | Counter confirmation | Total capped / games |
| --- | ---: | ---: | ---: | ---: | ---: |
| Inquisitor only | 1,076 | 8,497 | 74 | 572 | 10,219 / 627,168 |
| Allegiances + Ambassador | 642 | 3,351 | 4 | 2 | 3,999 / 640,704 |
| Allegiances + Inquisitor | 576 | 3,144 | 1 | 21 | 3,742 / 640,704 |
| Total | 2,294 | 14,992 | 79 | 595 | 17,960 / 1,908,576 |

For example, Truthful economy against Truthful opponents in ten-player Inquisitor-only confirmation had 1,015 capped games out of 10,000 (10.15%). Its reported win rate is not an estimate of who would eventually win those unfinished games.

## Interpretation limits

- Eight fixed strategies were screened; only two per rules option/player count were confirmed. An unconfirmed or untested strategy can still be stronger.
- The policies differ in several decisions at once. No expansion ablation study isolates conversion, reserve collection or examination.
- Opponents, card beliefs, clockwise response priority and automatic proof are model conventions. Negotiation, persuasion and learning between games are absent.
- Deck size changes with player count: three copies per role at two through six players, four at seven or eight, five at nine or ten. The first player starts with one coin in two-player games.
- The base studies use different policy populations and rule conventions. Expansion/base differences cannot be interpreted as a causal effect of adding the expansion.

## Evidence

This interpretation is derived from the completed [findings JSON](../research_results/2026-10-18-expansion/findings.json), SHA-256 `857745cc6f75c38e125275cb2c5a04120a16ef27d5c326956821e3df897904e6`, and the four saved stage summary CSVs. Counts, leaders, ties, rates, pair directions and capped-game totals were reconciled with those saved summaries. The [study protocol](EXPANSION_STUDY.md) and [rules review](EXPANSION_RULES.md) describe the design and model.

The passed [independent audit receipt](../research_results/2026-10-18-expansion/replay-audit.json) covers all 1,908,576 raw outcomes and 25,380 strict replays across 1,410 jobs, with matching frozen plan and source hashes. Replay shares the expansion engine. Independently authored transition tests assess the modeled rules separately. This interpretation does not substitute for the audit and test evidence.
