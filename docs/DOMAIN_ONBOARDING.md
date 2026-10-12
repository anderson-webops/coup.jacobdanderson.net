# Custom-domain activation handoff

Requested site: `https://coup.jacobdanderson.net/`.
Repository: `https://github.com/anderson-webops/coup.jacobdanderson.net`.
Published expanded release: [`v1.1.0`](https://github.com/anderson-webops/coup.jacobdanderson.net/releases/tag/v1.1.0), with annotated tag object `c86591d43ccc822bbbd816333993244f93479983` at source `ef14949540a4c2c251cc95c513509ddb5c530ab5`. Use its exact archive, `release-manifest.json`, and `SHA256SUMS`. The prior `v1.0.1` release is retained unchanged. The earlier `v1.0.0` tag is retained as an unaccepted candidate after CI found a test dependency on a local Git ignore setting.

## Current observed state, 12 October 2026

- Route53 public zone `jacobdanderson.net`, ID `Z08458053I46F5AMNP63`, now contains the approved Coup A and AAAA records shown below.
- Both records were explicitly approved by the user and created at 22:07:20 UTC on 12 October 2026. Change ID: `C10022743CO3ZAMWZ2HWM`. Route53 reports INSYNC and the authoritative nameserver returns both exact addresses.
- The reference `liarsdice.jacobdanderson.net` serves the verified static site through Nginx.
- Its Route53 records are A `45.17.197.196` and AAAA `2600:1700:1960:2adf::41`, each TTL 300. These records are preserved.
- At 23:06 UTC, public Coup HTTPS returned 200 over both exact IPv4 and IPv6 edge addresses. Both homepage bodies match the v1.0.1 digest `4d8eed601b9095dbb0ffa157f633ad44b928c43844cc8c1316771ec374db7384`, and the reviewed CSP and response headers are present. This verifies the original homepage, not the expanded candidate.
- At 2026-10-12T23:44:24.352983+00:00, direct IPv4 and IPv6 HTTPS returned 200 from the exact approved addresses, but `/publication.json` still identifies version `1.0.1` and has SHA-256 `85892bbdbf78707b09f040b247e9eb105f96b0dbd6cc7ffa1ce2ca184af374e4`. The expanded version is not publicly accepted. See [validation/v1.1.0-public-state.json](validation/v1.1.0-public-state.json).
- The new source repository and release are independent of production host onboarding.

## Completed exact DNS creation

The approved records match the Liar's Dice edge:

| Name | Type | TTL | Value |
| --- | --- | ---: | --- |
| coup.jacobdanderson.net. | A | 300 | 45.17.197.196 |
| coup.jacobdanderson.net. | AAAA | 300 | 2600:1700:1960:2adf::41 |

The user approved these exact records in this publication task before the mutation. The prior state was rechecked and preserved as absence; the mutation used atomic CREATE operations rather than overwriting records. Rollback removes only these newly created records after separately authorized rollback. The existing Liar's Dice and other domain records are preserved.

## Expanded research release

Version 1.1.0 contains the separately frozen expanded study, an independent replay receipt, strategy explanations, counter and component panels, and a complete downloadable evidence bundle. The release manifest and checksums are the exact asset and response-policy authority. Do not reuse earlier inline-script hashes with this release.

All 133 tests and the complete raw audit pass on the tagged source. [GitHub CI 38322612775](https://github.com/anderson-webops/coup.jacobdanderson.net/actions/runs/38322612775) passed every required gate. The Linux CI assets match the independently verified local package, and all three GitHub asset sizes and digests match.

| Asset | SHA-256 |
| --- | --- |
| `coup-site-v1.1.0-ef14949540a4.tar.gz` | `ee5b2cc59fd4d0bddec6172c53d915bf535f20b83f5661b3a9e991fbc212e0fc` |
| `release-manifest.json` | `160bb57d69ae5476ae41dcaeb959fb5a5631842ef930eaea576a8e82a3916506` |
| `SHA256SUMS` | `2c9a06b34c710efb8748b5dbb3ff373fb9df44ba93c6ab3ee11a586b2e404325` |

The expected expanded homepage SHA-256 is `0a3515624d6ce4ce7d4eb82fe0ab9022775bf4415728711be326b4b7e15a3868`. Source/release proof is retained in [validation/v1.1.0-source.json](validation/v1.1.0-source.json). Public acceptance is separate; no server-side activation status was available to this source task.

## Protected host work

The protected operator or server automation must stage the expanded immutable release, affirm the capabilities declared in `deployment-contract.json`, stage the exact immutable archive, preserve working domain routing and TLS, and apply the release's `site_policy` headers. The script policy for Coup includes exact inline-script hashes; Liar's Dice's `script-src 'none'` policy cannot be copied unchanged because Coup's filters require the reviewed script.

Only `dist/` is public. No application process, database, credentials, or writable state is needed. Keep release control files outside the public root. Confirm exact homepage and asset hashes and the missing-path 404 over both HTTPS address families before accepting activation. Honor the first-activation absent-state rollback and retain immutable releases afterward.

Source agents must not connect to or administer the host. A GitHub release, passing CI, or new DNS record alone does not prove that the requested site is serving the accepted bytes.
