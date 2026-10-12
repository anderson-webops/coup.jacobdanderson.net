# Extended base-game rules test review

The additional `test_extensive_rules.py` suite exercises the frozen Coup engine without changing the 10 October study inputs, outputs, or publication anchor. Its fixtures place all 15 physical cards among hands, face-up losses, and the Court deck. Every transition test checks the resulting state, and seeded games check conservation and action legality after each live turn.

## Rules checked

The [original Coup rulebook](https://www.qugs.org/rules/r131357.pdf) specifies two cards per player, three copies of each role, the first player's one-coin start in a two-player game, one action per turn, the mandatory Coup at 10 coins, challenge order, card replacement after a proved claim, action-cost refunds after a disproved action, and costs remaining spent after a successful counteraction. It explicitly allows two influence losses during one unsuccessful assassination defense. The [publisher-maintained Dized rules](https://rules.dized.com/game/xzsTtI3VTV-2wvos3otxIg/coup) confirm that [Captain or Ambassador may block Steal](https://rules.dized.com/game/xzsTtI3VTV-2wvos3otxIg/2Al0_fOmQZ-ka_XVFCyQJA/block-steal-ambassador-or-captain).

The suite covers Income, Foreign Aid, Coup, Tax, Assassinate, Steal, and Exchange; truthful and false action and block challenges; actor and target elimination; Assassin refunds and spent fees; one- and two-influence exchanges with duplicate cards; public card exposure and private-card isolation; clockwise response selection; and winner attribution by seat. Cases that force an action replace only the policy's action or target choice, leaving the engine's challenge, block, and outcome resolution active. Randomized two- through six-player games check card conservation, nonnegative coins, target validity, and affordable Coup and Assassination actions after every step.

## Scope boundary

The engine accepts only its built-in policies and does not expose a validated external action-submission API. Tests therefore do not inject illegal actions or assert that `step()` rejects a monkeypatched illegal choice. Its automatic proof of a held role, influence-discard heuristic, and clockwise response priority are legal policy and reproducibility choices, not the only choices available to people playing Coup. Negotiation and the optional two-player variant remain outside this base-game model. A passing test suite does not by itself establish an optimal strategy or validate statistical claims from a separate study.

One Steal edge follows the rulebook's general statement that an eliminated player immediately returns all coins to the Treasury: if a false block challenge eliminates the target, the eventual Steal transfers zero. A later printed example depicts a transfer after elimination. The test records the engine's stated interpretation of that inconsistency; it does not claim the example is a second rule.

Run the additional suite with `python3 -B -m unittest -v test_extensive_rules`.
