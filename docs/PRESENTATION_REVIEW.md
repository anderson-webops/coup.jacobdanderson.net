# Statistics and strategy presentation review

## Request

Jacob requested a Coup page focused on statistics and strategy recommendations/analysis, using the Liar’s Dice recap and Zilch stats/help area as references.

## Changes in v1.1.1

The page opens with conditional recommendations derived from the frozen equal-field averages. Main comparisons, weakest-field rates, targeted counters and strategy component results remain prominent. Earlier results and individual strategy descriptions are collapsed. The decorative card hero, rules tutorial, engineering/testing narrative, evidence download rails and duplicate strategy grids were removed. Statistical interpretation remains beside the numbers.

Only three public files changed: `index.html`, `site.css` and `publication.json`. The embedded study-data bytes, all 25 evidence files, the favicon and frozen execution source hashes are unchanged. The publication checker and its evidence gates were preserved.

## Verification

- All 133 required tests passed locally and in exact-source GitHub CI 38337042262.
- The independent raw audit reconciled all 2,814,728 expanded outcomes.
- Browser checks matched all 560 displayed rows across 35 main matchups, 16 main profiles, 24 earlier panels and all 11 earlier profiles.
- Widths 360, 390, 768 and 1440 pixels had no page overflow. Desktop and phone views were visually reviewed. No browser errors or warnings occurred.
- Challenge low’s description was checked against the frozen engine: its 15% random challenge chance applies to Assassin, Captain and Contessa claims.
- Isolated 29-file publication and release checks passed. The local, Linux CI and uploaded release assets have matching hashes.
- The outgoing diff passed a redacted local secret scan. Existing hook delegation remained in place.

The immutable release is [v1.1.1](https://github.com/anderson-webops/coup.jacobdanderson.net/releases/tag/v1.1.1) at `3e5ace43c9734c61d5df43a592ab9bdb8311b358`. See [the source/release receipt](validation/v1.1.1-source.json). At 2026-10-13T02:36:13.326278+00:00, direct HTTPS publication identities were ipv4=1.1.0, ipv6=1.1.0. The v1.1.1 public acceptance gates have not passed. See [the public-state receipt](validation/v1.1.1-public-state.json).
