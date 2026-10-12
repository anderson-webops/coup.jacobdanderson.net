# Custom-domain activation handoff

Requested site: `https://coup.jacobdanderson.net/`.
Repository: `https://github.com/anderson-webops/coup.jacobdanderson.net`.
Expanded candidate release: `v1.1.0`; use its exact annotated tag, source commit, archive, `release-manifest.json`, and `SHA256SUMS`. The prior `v1.0.1` release is retained unchanged. The earlier `v1.0.0` tag is retained as an unaccepted candidate after CI found a test dependency on a local Git ignore setting.

## Current observed state, 12 October 2026

- Route53 public zone `jacobdanderson.net`, ID `Z08458053I46F5AMNP63`, now contains the approved Coup A and AAAA records shown below.
- Both records were explicitly approved by the user and created at 22:07:20 UTC on 12 October 2026. Change ID: `C10022743CO3ZAMWZ2HWM`. Route53 reports INSYNC and the authoritative nameserver returns both exact addresses.
- The reference `liarsdice.jacobdanderson.net` serves the verified static site through Nginx.
- Its Route53 records are A `45.17.197.196` and AAAA `2600:1700:1960:2adf::41`, each TTL 300. These records are preserved.
- At 23:06 UTC, public Coup HTTPS returned 200 over both exact IPv4 and IPv6 edge addresses. Both homepage bodies match the v1.0.1 digest `4d8eed601b9095dbb0ffa157f633ad44b928c43844cc8c1316771ec374db7384`, and the reviewed CSP and response headers are present. This verifies the original homepage, not the expanded candidate.
- The new source repository and release are independent of production host onboarding.

## Completed exact DNS creation

The approved records match the Liar's Dice edge:

| Name | Type | TTL | Value |
| --- | --- | ---: | --- |
| coup.jacobdanderson.net. | A | 300 | 45.17.197.196 |
| coup.jacobdanderson.net. | AAAA | 300 | 2600:1700:1960:2adf::41 |

The user approved these exact records in this publication task before the mutation. The prior state was rechecked and preserved as absence; the mutation used atomic CREATE operations rather than overwriting records. Rollback removes only these newly created records after separately authorized rollback. The existing Liar's Dice and other domain records are preserved.

## Expanded research candidate

Version 1.1.0 contains the separately frozen expanded study, an independent replay receipt, strategy explanations, counter and component panels, and a complete downloadable evidence bundle. The release manifest and checksums are the exact asset and response-policy authority. Do not reuse earlier inline-script hashes with this candidate.

## Protected host work

The protected operator or server automation must stage the expanded immutable release, affirm the capabilities declared in `deployment-contract.json`, stage the exact immutable archive, preserve working domain routing and TLS, and apply the release's `site_policy` headers. The script policy for Coup includes exact inline-script hashes; Liar's Dice's `script-src 'none'` policy cannot be copied unchanged because Coup's filters require the reviewed script.

Only `dist/` is public. No application process, database, credentials, or writable state is needed. Keep release control files outside the public root. Confirm exact homepage and asset hashes and the missing-path 404 over both HTTPS address families before accepting activation. Honor the first-activation absent-state rollback and retain immutable releases afterward.

Source agents must not connect to or administer the host. A GitHub release, passing CI, or new DNS record alone does not prove that the requested site is serving the accepted bytes.
