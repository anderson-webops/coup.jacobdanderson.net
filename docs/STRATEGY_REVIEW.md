# Coup strategy review for the next study

This is a research design and interpretation guide, not a new result set. The
validated 10 October 2026 study remains in [FINDINGS.md](../FINDINGS.md). Its
four-player leaders changed with the opponent field: Bluff heavy against honest
baseline opponents, Challenge heavy against bluff-heavy opponents, and Exchange
against challenge-heavy and mixed opponents. Those results compare the named
simple policies and do not establish a universally best Coup strategy.

The next study should ask which decisions improve *game win probability* when a
policy has only its own cards and public information. It should retain the old
study intact, use new source and seed panels, and report the tested opponents and
player counts alongside every ranking.

## What the existing comparison actually tests

The current [`Game`](../coup_simulator.py) supplies each policy its own cards
and coins, plus every player's coins, influence count, and revealed cards. Its
policies share an immediate Coup at seven coins, the same target rule, a fixed
influence-discard order, a fixed Exchange keep order, and a fallback to Income
after two failed actions. They differ mainly in action claims, challenges, and
blocks. The opponent fields consist of baseline, frequent bluffer, frequent
challenger, and a rotation of those three.

This makes the first result useful but narrow. For example, `challenge_heavy`
challenges every claim, while `bluff_heavy` claims Tax every eligible turn.
Their matchup supports a *mechanism hypothesis* that challenges punish frequent
bluffs. It does not isolate an optimal challenge threshold, because the same
policies also vary action mix and produce different game states. The prior
screening was exploratory across two to six players; the held-out comparison
confirmed four-player finalists against those four fields. The small mixed-field
lead should not be extrapolated to new opponent populations.

The most important missing decisions are context-sensitive challenges, selective
bluffs and blocks, opponent and target choice, when to spend coins, and which
card to keep or reveal. The present observation has no public action history,
even though the engine records events internally. An adaptive policy needs a
public-only event history or bounded summary, including claims, challenges,
proofs, disprovals, blocks, and exchanges. It must never receive other players'
hidden cards, deck order, or future randomness.

## Public information and card beliefs

The base deck has three copies of each of five roles. Let `h_r` be copies of
role `r` in the acting player's current hand, `f_r` be copies publicly revealed
by all players, `U = 15 - own_hand_size - all_revealed_cards`, and
`m_r = 3 - h_r - f_r`. If an opponent has `k` hidden influence and unknown
cards are otherwise exchangeable, a useful starting prior is:

```text
P(opponent holds at least one r) = 1 - C(U - m_r, k) / C(U, k)
```

For one hidden card this reduces to `m_r / U`. A role with all three copies
accounted for in one's hand and public discards has zero probability. This is
only a *card-availability prior*. Claims, challenges, revealed proof cards,
exchanges, and selective opponent behavior change the posterior. A card shown
to prove a claim returns to the deck and is replaced; the proof is evidence
about the prior hand, not permanent knowledge of the new hand. Exchange
increases uncertainty about what the player currently holds. Store public
events with their order so a belief updater can distinguish these cases.

For a claim in context `x`, a simple behavioral update is:

```text
p = P(holds claimed role | public cards and exchange history)
a = P(makes this claim | holds role, x)
b = P(makes this claim | lacks role, x)
P(truthful | claim, x) = a*p / (a*p + b*(1-p))
```

Estimate `a` and `b` from independent training games with smoothing, or use
predeclared opponent types. Do not infer a player is honest merely because a
claim went unchallenged. Do not learn from a simulated opponent's hidden state
inside a game; only public revelations may update the live policy. Estimate
separate likelihoods for Tax, Steal, Assassin, Exchange, and each block. A
Contessa claim under lethal pressure is not interchangeable with a routine Duke
Tax claim.

## Decisions worth testing

### Challenge an action or block

The challenge is a wager of influence and tempo. In a rough state-value model,
challenge when:

```text
(1 - p_true) * G_false > p_true * L_true
```

`G_false` is the gain from exposing a false claim, including the claimant's
lost influence and the resulting cancelled action or failed block. `L_true` is
the loss if the claim is proved, including the challenger's lost influence and
the action or block still resolving. Equivalently, when both terms are positive,
challenge for `p_true < G_false / (G_false + L_true)`. These terms should be
estimated from the current game state or a bounded rollout. A fixed challenge
percentage ignores the size and beneficiary of each action.

For an Assassin claim, a target that challenges a truthful claim can lose one
card to the challenge and another to the assassination. The current rules
engine also distinguishes a successful challenge to the Assassin *action*,
which refunds its three-coin fee to a surviving claimant, from a successful
Contessa *block*, which leaves that fee spent. A false Contessa block that is
challenged can let the assassination proceed after the blocker loses an
influence. These transitions make the threshold highly sensitive to whether
the challenger is the target, whether either player has one influence, and
whether the action would eliminate a player. The [Coup counteraction rules](https://rules.dized.com/game/xzsTtI3VTV-2wvos3otxIg/b4b0aSGGR_2wFKUAwit1Kw/counter-actions)
and [Contessa example](https://rules.dized.com/game/xzsTtI3VTV-2wvos3otxIg/vn1Jy3lnRzq-_-YW0Poqeg/block-assassinate-contessa)
make the action/block sequence and possible two-card loss explicit.

Start with transparent threshold policies and compare them with one-step or
short-rollout state values. Track *attempted* challenges, truth rate among
challenged claims, influence gained/lost, and wins by claim type. A high
challenge success rate alone is not a sufficient objective if the missed
actions are more costly than failed challenges.

### Claim an action and choose a target

An unheld role can be claimed, but its expected value depends on challenge
probability, block probability, and influence at risk. For a bluff:

```text
V(bluff) ≈ (1 - q_challenge) * V(action after possible blocks)
           - q_challenge * C(lost influence and turn)
           + future information effects
```

This is a decision sketch, not an exact equation. The action value should
include other players' changed state, not just coins gained. Tax yields three
coins if it resolves. Steal transfers up to two coins, so stealing one coin
from a weak player has a different effect from taking two from an imminent
seven-coin threat. Assassin costs three coins and can be stopped by a Contessa
claim. An honest claim can itself invite a challenge that costs an opponent an
influence and replaces the proved card.

Target evaluation should include whether one influence would eliminate the
opponent, their coins relative to seven and ten, who acts before the focal
player's next turn, their known or likely defenses, and likely retaliation.
Coins have nonlinear value near the Coup thresholds: Coup costs seven and a
turn beginning at ten or more requires it. Income guarantees one coin, Foreign
Aid can give two if no Duke blocks, Tax can give three if its claim survives,
and Steal transfers `min(2, target_coins)` if it resolves. A tactical Coup at
seven and saving for a later Coup are both legitimate candidates; the present
policies always take the former. In multiplayer, eliminating a weak player may
help a different rival most, so compare *focal win probability* rather than
maximizing damage alone.

### Block, discard, and exchange

A truthful block prevents the action and may punish a challenger, though
proving the card changes the hand. A bluff block risks an influence. Foreign
Aid may be blocked by any Duke claimant; only the target may block Steal with
Captain or Ambassador or Assassin with Contessa. Test selective block policies
that weigh the prevented harm against challenge risk and future table position.
Give Contessa bluffing a separate, conservative parameter: if it is challenged
and false, the same target may then suffer the assassination.

The existing static discard and Exchange rankings overvalue one role in every
state. Consider card retention as a choice over every legal *multiset* of cards
available after drawing two. Duke offers Tax and a Foreign Aid block; Captain
offers Steal and a Steal block; Assassin's action depends on available coins and
victim defenses; Contessa is valuable under assassination pressure; Ambassador
offers hand improvement and a Steal block. Evaluate role pairs for diversity,
defense, and duplicate resilience, then test a simple state-dependent score
against a shallow public-belief rollout. On losing influence, compare the value
of the two possible remaining hands rather than always discarding Contessa.

## Candidate policy families and counters

Freeze named versions and exact parameters before held-out evaluation. These
are *search proposals*, not recommended settings or measured winners:

| Family | Main variation | Counter to test |
| --- | --- | --- |
| Honest economy | Truthful claims; Income, Foreign Aid, and Coup timing; threat-aware target | Duke blocks and selective Tax bluffs |
| Tax opportunist | Tax bluff probabilities such as 0, 0.15, 0.4, 0.75 by public exposure and challenge risk | Calibrated Duke challenges |
| Steal pressure | Target coins and next-turn Coup threat; low-coin target avoidance | Captain/Ambassador blocks and selective block challenges |
| Assassin timing | One-influence elimination versus urgent two-influence threat; expected Contessa resistance | Contessa retention, selective block, and defensive Coup |
| Belief challenger | Availability prior plus claim likelihood; utility multiplier such as 0.5, 1, or 2 on risk of losing influence | Honest claims and safe economy |
| Selective blocker | Separate Duke, Steal, and Contessa block decisions; low/moderate/aggressive bluff rates | Block challenges calibrated to the action at stake |
| Hand manager | State-dependent Exchange keep and influence discard; duplicate versus diverse pair value | Coup pressure and an opponent that steals or assassins often |
| Adaptive mixture | Randomize among predeclared policies using public observations only | Targeted opponents and a varied field |

Avoid a huge full factorial grid. Screen individual mechanisms and a limited
set of combinations on a training panel, then search a bounded number of
counter variants. Include the old named policies as controls. Test counters
against the policy they target *and* varied populations: a narrow counter can
win one matchup and lose broadly. Opponent models should include honest,
habitual bluffer, selective bluffer, over-challenger, passive challenger,
aggressive blocker, exchange-heavy, economy/Coup pressure, and mixtures.
Create at least one policy that changes behavior after public evidence and an
otherwise identical non-adaptive ablation to isolate the value of learning.

### Audit of the current research policy implementation

[`research_strategies.py`](../research_strategies.py) is a finite, interpretable
heuristic set. Its card-availability calculation is the exact hypergeometric
prior under uniform unknown-card allocation, and Foreign Aid uses the same
allocation to estimate that no opponent holds Duke. These are not exact
posteriors after behavioral evidence. Claim credibility uses one assumed bluff
parameter and a smoothed count of each opponent's publicly proved and
disproved claims, without separating roles, action pressure, or exchanges.
Its history-sensitive bluff response uses a table-wide challenge rate. Those
choices can be tested, but should not be described as calibrated Bayesian play.

Action scores are hand-chosen utility proxies rather than estimated win
probabilities. Every held valid block is attempted; the `block_bluff` parameter
only governs a missing-role block, with a forced desperate Contessa attempt for
a one-influence assassination target. Target scoring uses visible coins,
influence, and simple card priors; it does not model turn order or retaliation.
Exchange and influence discard use an additive value for each role, so they do
not capture pair synergy. `public_random` samples legal actions uniformly but
still uses its ordinary response, target, and retention rules; it is an action
randomization control, not an entirely random player.

The ablation names describe their exact scope. `ablate_no_claim_cards` removes
card availability from claim credibility and the impossible-claim challenge
shortcut, while action and target scores can still use card availability.
`ablate_no_history` removes both proof-record learning and table-wide challenge
pressure. `ablate_random_target` changes target selection and the expected
value of targeted actions. `ablate_fixed_retention` restores both fixed
Exchange keeps and fixed influence discard. These are local, sometimes bundled
component comparisons; none alone identifies a general causal effect of
"information" or "adaptation." Their direction and size require held-out
outcome evidence.

Each policy function receives a public-only view plus its own cards. The game
uses a separate deterministic decision stream for each seat, apart from deck
shuffling. This is a boundary for the named policy functions, not a secrecy
guarantee for arbitrary code that can inspect the `ResearchGame` object or
reconstruct a published seed. Keep the runner's policy interface narrow and
check hidden-state invariance before interpreting the experiment.

## Evidence plan and interpretation

1. Lock the rules profile and verify every transition: card conservation,
   duplicate Exchange cards, challenge/action/block order, fees, two-card-loss
   cases, elimination, two-player first-seat coin rule, and legal actions.
   Add a test that two games with the same public history and own hand but
   different hidden opponent hands give the policy the same decision when its
   policy random stream is held fixed.
2. Give each policy only public history and its own hand. Separate deck,
   opponent, and focal-policy random streams. Use stable seeds, unique focal
   identity, identical opponent panels for pairwise candidates, and complete
   seat rotations. Preserve per-rotation outcomes and analyze them as blocks.
3. Split screening, tuning, counter discovery, revalidation, and confirmation
   into independent seed panels. Freeze candidates, parameters, opponent
   populations, player counts, sample sizes, comparison family, and scoring
   before confirmation. Search on earlier panels only.
4. Confirm at multiple player counts and report each separately. Two-player
   results need full seat balance because the starting player begins with one
   coin in this rules profile. Report win rate by field and seat, pairwise
   differences on matched blocks, uncertainty covering the predeclared family,
   and the worst tested field alongside any average. Keep draws in the stated
   denominator and show cap frequency and turn length.
5. Save raw outcomes, policy parameters, opponent rosters, phase/seed IDs,
   source hashes, and diagnostics: action/claim/block/challenge counts, bluff
   and proof rates, challenge accuracy, coins transferred, influence lost by
   cause, and elimination timing. Distinguish exploratory patterns from
   held-out claims. Do not overwrite or relabel the frozen first study.

The Liar's Dice research is a useful *method* example. Its large study separated
search from frozen confirmation, rotated every seat, retained block-level
outcomes, and tested targeted counters against varied fields. In that study,
response-learning counters gained against selected Perudo targets but four
multiplayer counters lost to their corresponding mixed-field leader. That is a
warning about specialization, not a Coup result. Its observed zero
*deliberate* bluff parameter among selected two-player leaders cannot be
transferred to Coup: claims, blocks, influence loss, and economics make a
different game. Likewise an empirical mixture over tested policies is a
restricted policy-game calculation, not a solved equilibrium.

The practical endpoint is a conditional guide: which tested policy performs
well for a given player count, opponent mix, and risk tolerance; which specific
counter has held-out support; and which comparisons remain unresolved. The
public site should present that scope next to each number.
