# Coup strategy simulator

Reproducible initial simulator for standard base Coup (3–6 players; 2-player games are accepted for exploratory use but the standard setup is not claimed). It models the five roles (three copies each), income, foreign aid, tax, steal, exchange, coup, challenges, blocks, influence loss, replacement draws and elimination. Policies receive only their own hidden cards plus public state; there is no opponent-card oracle.

## Rules and scope

The baseline is the original standard game: two influence cards and two coins, 15-card court deck, mandatory coup at 10 coins, and only one winner. The implementation does not include Reformation, Inquisitor, team rules, optional two-player setup, negotiations, or human communication. The publisher/rulebook text used for verification is archived online at [Indie Boards & Cards / Coup rules PDF](https://www.qugs.org/rules/r131357.pdf) (the PDF credits Rikki Tahta, La Mame Games, and Indie Boards & Cards). A concise mirror of the original 3–6 player rules is [Coup Rules PDF](https://boardgame.bg/coup%20rules%20pdf.pdf). Retrieved 2026-10-10; URLs are retained because rules editions and variants differ.

Edition note: the eight-page Dystopian Universe rulebook states that challenges resolve before blocks, any non-actor may challenge an action or counteraction, and the Assassin's 3-coin fee remains spent when Contessa successfully blocks (printed pp. 3–5; [scan](https://www.buffalolib.org/sites/default/files/gaming-unplugged/inst/Coup%20Instructions.pdf)). A successful challenge of the Assassin claim refunds the fee. This simulator follows that timing and cost rule. It also follows the booklet's general rule that an eliminated player's coins return to the Treasury; therefore a target eliminated while its block is challenged has no coins available to steal. This differs from the printed Sacha/Haig example, which appears to award a steal after the target's elimination; that example is treated as an inconsistency, not a separate variant.

Responder convention: the booklet permits any opponent to challenge but does not define a total order when several respond simultaneously. For reproducibility, this simulator resolves responders in clockwise player-index order and accepts the first applicable challenge/block; this is a modeling convention, not an official priority rule. The Japanese publisher correction page ([New Games Order](https://www.newgamesorder.jp/games/coup)) describes one simultaneous challenge counting, negotiation, and otherwise none if unresolved. Experiments should rotate seat assignments and should not treat this convention as uniquely official. Action challenges and block challenges remain successive phases, as in the English rulebook.

## Run

```sh
python3 -m unittest -v
python3 coup_simulator.py --players 4 --games 10000 --seed 20261010
python3 run_experiments.py > results.csv
```

The seed means game `k` uses `seed+k`; rerunning gives identical output. `experiment()` supports controlled policy lists, e.g. `['taxer','baseline','captain','foreign_aid']`. Results are win shares, not equilibrium probabilities. Use multiple seeds, balanced seat permutations, and binomial intervals before making claims; this starter harness does not yet provide full confidence intervals or a policy search.

The checked-in runner evaluates one focal policy against `n-1` `baseline` opponents, rotates the focal seat through every seat, and runs 1,000 games per seat using evaluation seeds `20261010 + seat*100000 + game_index` (no tuning seeds are mixed in). `benchmark_policies.py` adds bluff-heavy, challenge-heavy, heterogeneous, and two-player tables. It reports wins, non-draw denominator, draws/turn caps, and per-seat Wilson 95% intervals. Seat blocks are intentionally kept separate because seat results are correlated; do not pool them as independent observations. Baseline uses random legal actions, truthful eligible blocks, and challenges claims made publicly impossible by three exposed copies; it is a competent baseline for rule coverage, not a strong or optimal strategy. Bluff-heavy always claims tax when it can and claims blocks; challenge-heavy challenges every character claim. These are interpretable stress-test policies, not optimal play.

## Known limits

The built-in policies are deliberately simple baselines for an initial executable research object, not strong or optimal play. Challenge/block behavior is policy-driven and does not model negotiation or sophisticated belief updates. Exchange deck-return logic is deterministic only up to the seeded RNG. Further work should add event traces, legal-action assertions, seat balancing, confidence intervals, and stronger information-state policies before interpreting strategy differences.
