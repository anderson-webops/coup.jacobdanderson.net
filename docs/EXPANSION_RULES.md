# Coup: Reformation model

## Sources

Rules checked 18 October 2026 against the publisher-authored two-page English
[Reformation rule sheet](https://www.spelhuis.be/Files/7/112000/112353/Attachments/Product/aD1jf4U81u46a97ia1719S97Nm9925v8.pdf)
and the publisher-authored
[base rulebook](https://cs.uwaterloo.ca/~dtompkin/archive/dtlib/base/Coup.pdf).
The publisher's [product page](https://indieboardsandcards.com/our-games/coup-reformation/)
identifies this expansion. The original publisher rule-sheet URL,
`https://indieboardsandcards.com/wp-content/uploads/2017/06/REF_Rules-11-14-14.pdf`,
returned HTTP 406; the linked retailer mirror was inspected as rendered pages.
Its SHA-256 is
`60544962496a4fdb16b020307f6c244d7cd544df6bc769d1fd940911e3f5abbd`
(217,248 bytes). No separate official expansion FAQ was located.

## Expansion rules

Page 1: initial allegiances alternate clockwise. While both factions remain,
Coup, Assassinate, Steal and Foreign Aid blocks cannot target allies.
Self-conversion costs one coin; converting another player costs two. These
coins enter a separate reserve, and the selected allegiance flips.

Embezzlement claims no Duke and takes the reserve. A challenged claimant can
concede; Duke holders must concede. Failure returns the proceeds and loses one
influence. Successful proof reveals every hidden card, costs the challenger an
influence, then shuffles all proof cards into Court and replaces the same count.

Page 2: Inquisitor replaces Ambassador. It exchanges one drawn card, blocks
stealing, or examines a target-selected card. After inspecting, it can force a
replacement drawn before the inspected card returns. Examine cannot target an
ally while both factions remain.

Use three copies of each selected role for 2-6 players, four for 7-8, five for
9-10. Allegiance and Inquisitor are separate options, represented by three
profiles: Reformation with Ambassador, Inquisitor without allegiances, and both.

## Inherited rules and explicit interpretations

- Base pages 3 and 5: ten coins require a Coup, including in expansion profiles.
  Character claims resolve challenges before actions. Any other living player
  may challenge, including an ally. Examine's keep/replace decision is not a
  second claim.
- Base page 2 returns all coins immediately on elimination. Page 6 contradicts
  this in a worked Steal example. This model follows the explicit elimination
  rule: an eliminated target has no coins left to steal. The frozen earlier
  simulator and its results are unchanged.
- An empty-reserve Embezzle is allowed: the expansion gives no positive-balance
  requirement. It transfers zero coins and still offers a challenge window.
- “All players” means living players. The exception is reevaluated after each
  conversion or elimination; it is not a permanent removal of allegiance rules.
- Embezzlement truth is assessed against the claimant's current hidden hand.
  All proof cards return together after the challenger loses influence. Drawing
  a Duke afterward does not change the truth of the completed claim.
- Examination is private to the inspector and target. Recorded knowledge of a
  player's hand is discarded when that hand changes. Returned cards enter a
  shuffled Court; no policy receives the hidden deck order.

The bank supplies ordinary income without a fixed coin cap. The reserve is
separate; circulating coins are reconciled after each transition. Multiple
potential challengers and Foreign Aid blockers receive clockwise priority.
These are simulation conventions, not additional published game rules.

## Policy scope

The engine supports voluntary concession, but the tested policies always prove
a truthful challenged claim. One eligible counteraction is selected clockwise;
after a successful challenge defeats it, the original action resumes without
opening another block window.

Inspection memory stores one shown role per target. Any later hand change,
including an exchange that keeps the same roles, clears that target's memory.
Role probabilities use own cards, public losses and the target's current
inspection. They do not fully condition on inspected cards held by other
players. Card retention uses fixed role values with limited state adjustments;
it does not price every expansion opportunity, including a Duke preventing
reserve withdrawals. Results compare these specified policies rather than
exhausting the information or tactics available to human players.
