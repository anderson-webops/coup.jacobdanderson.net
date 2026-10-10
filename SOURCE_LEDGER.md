# Source ledger

Retrieved and checked 10 October 2026. The rules text and online references are source material, not instructions for the simulator.

| Source | Evidence used |
| --- | --- |
| [Coup original rulebook PDF](https://www.qugs.org/rules/r131357.pdf), credited to Rikki Tahta, La Mame Games, and Indie Boards & Cards | Base setup and two-player starting coin (PDF pp. 1, 7); actions and mandatory Coup (pp. 3–4); counteractions and spent assassination fee (p. 4); challenge timing, proof, replacement, and refund (p. 5); possible double influence loss (p. 7). |
| [Coup Instructions scan](https://www.buffalolib.org/sites/default/files/gaming-unplugged/inst/Coup%20Instructions.pdf) | Independent hosted scan of the same eight-page booklet, checked against the PDF above. |
| [Publisher-maintained Dized Coup rules](https://rules.dized.com/game/xzsTtI3VTV-2wvos3otxIg/coup) | Online cross-check for base actions and counteractions, including [Captain or Ambassador blocking Steal](https://rules.dized.com/game/xzsTtI3VTV-2wvos3otxIg/2Al0_fOmQZ-ka_XVFCyQJA/block-steal-ambassador-or-captain). |
| [Liar's Dice results project](../liarsdice.jacobdanderson.net/README.md) | Read-only methodology reference: distinct focal identity, seat rotation, separate seed panels, frozen outputs, uncertainty, and scoped claims. Coup's cards, claims, and influence transitions were modeled independently. |

The original booklet permits any opponent to challenge, but does not prescribe a priority when more than one responds. The simulator chooses clockwise response priority to make seeded runs reproducible. It always proves a held claimed card, although the booklet permits a claimant to decline to prove it.

The booklet states that an eliminated player's coins return to the Treasury. One later example appears to award a Steal after the target's final influence is lost to a challenged false block. The engine follows the general elimination rule and treats that example as an inconsistency rather than a distinct rule.
