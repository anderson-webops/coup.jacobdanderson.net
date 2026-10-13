# Coup public activation handoff

## Current request and delivery checkpoint

Last actual request: “remove all of the extraneous informaiton that doesn't deal directly with statistics and strategy recommendations/analysis.” The focused page and its immutable source release are complete. Chat answer-delivery status is unknown in this file; the receipt establishes source/release delivery, not whether the final chat response has been sent.

Domain: `https://coup.jacobdanderson.net/`. Repository: `https://github.com/anderson-webops/coup.jacobdanderson.net`.

Latest release: [v1.1.1](https://github.com/anderson-webops/coup.jacobdanderson.net/releases/tag/v1.1.1), annotated tag object `2140fcc918102fb13c22ab7923542df6e839dcdb`, source `3e5ace43c9734c61d5df43a592ab9bdb8311b358`. All 133 tests and exact-source [GitHub CI 38337042262](https://github.com/anderson-webops/coup.jacobdanderson.net/actions/runs/38337042262) passed. Local, Linux CI and GitHub assets have matching hashes. See [source/release proof](validation/v1.1.1-source.json) and [presentation review](PRESENTATION_REVIEW.md).

## Public observation and next action

At 2026-10-13T02:36:13.326278+00:00, direct HTTPS publication identities were ipv4=1.1.0, ipv6=1.1.0. The v1.1.1 public acceptance gates have not passed. See [the public-state receipt](validation/v1.1.1-public-state.json).

Protected server automation must activate the exact v1.1.1 release, then verify all 29 file hashes, required response headers and real 404 over both HTTPS address families.

## Retained domain configuration

The explicitly approved Route53 CREATE change `C10022743CO3ZAMWZ2HWM` created only these two records on 12 October 2026; its completed INSYNC receipt is retained in the earlier publication evidence. No DNS or production configuration was changed during the presentation task. Preserve both records, working routing and TLS.

| Name | Type | TTL | Value |
| --- | --- | ---: | --- |
| coup.jacobdanderson.net. | A | 300 | 45.17.197.196 |
| coup.jacobdanderson.net. | AAAA | 300 | 2600:1700:1960:2adf::41 |

## Exact immutable release assets

| Asset | SHA-256 |
| --- | --- |
| `coup-site-v1.1.1-3e5ace43c973.tar.gz` | `5848c612c8055fba5a1fbb2aa98eb5fdc6900831d714409fcf8f085651396907` |
| `release-manifest.json` | `16e9db55174446b7210485dbd30254b0d01d942002b32d4e5fe3575cbde0792e` |
| `SHA256SUMS` | `4fdad1c7a5e3bbbaf10dfbadde2dbc888cf1e4bdb447326f59a81f939ac4ee39` |

Homepage SHA-256: `3ba28eddaed74403ab73c1995927a87e5bfdf32a8399889f3647ae74f6985eeb`. Version 1.1.1 changes presentation only; all frozen research and evidence bytes are unchanged. Earlier application tags and releases remain immutable.

## Protected hosting requirements

Only the archive’s `dist/` contents belong in the public root. The manifest’s `site_policy` supplies exact inline-script hashes and all required headers. Keep release controls outside the public root. Confirm the declared capabilities in `deployment-contract.json`, preserve immutable rollback releases and verify exact asset bytes, response headers and missing-path 404 over both HTTPS address families.

Source agents must not connect to or administer production. Protected server automation owns staging and activation. A source push or GitHub release alone does not prove public activation.
