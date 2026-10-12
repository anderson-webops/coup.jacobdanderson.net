# Custom-domain activation handoff

Requested site: `https://coup.jacobdanderson.net/`.
Repository: `https://github.com/anderson-webops/coup.jacobdanderson.net`.
Candidate release: `v1.0.1`; use its exact annotated tag, source commit, archive, `release-manifest.json`, and `SHA256SUMS`. The earlier `v1.0.0` tag is retained as an unaccepted candidate after CI found a test dependency on a local Git ignore setting.

## Current observed state, 12 October 2026

- Route53 public zone `jacobdanderson.net`, ID `Z08458053I46F5AMNP63`, has no record for `coup.jacobdanderson.net`.
- Public DNS queries return NXDOMAIN for both A and AAAA.
- The reference `liarsdice.jacobdanderson.net` serves the verified static site through Nginx.
- Its Route53 records are A `45.17.197.196` and AAAA `2600:1700:1960:2adf::41`, each TTL 300. These records are preserved.
- The reference edge rejects the Coup TLS hostname over both IPv4 and IPv6 when probed with the hostname and exact edge addresses. A working Coup virtual host has not been established.
- The new source repository and release are independent of production host onboarding.

## Proposed exact DNS creation

If the protected host accepts this site on the same edge as Liar's Dice, create only these new records:

| Name | Type | TTL | Value |
| --- | --- | ---: | --- |
| coup.jacobdanderson.net. | A | 300 | 45.17.197.196 |
| coup.jacobdanderson.net. | AAAA | 300 | 2600:1700:1960:2adf::41 |

This is a proposal requiring explicit authorization for the exact records under shared Sites policy. No DNS mutation has been made by this source-delivery task. The recorded prior state for both proposed records is absence; rollback removes only these newly created records after separately authorized rollback. Never alter the existing Liar's Dice or other domain records.

## Protected host work

The protected operator or server automation must onboard the canonical repository and release type, affirm the capabilities declared in `deployment-contract.json`, stage the exact immutable archive, configure domain routing and TLS, and apply the release's `site_policy` headers. The script policy for Coup includes exact inline-script hashes; Liar's Dice's `script-src 'none'` policy cannot be copied unchanged because Coup's filters require the reviewed script.

Only `dist/` is public. No application process, database, credentials, or writable state is needed. Keep release control files outside the public root. Confirm exact homepage and asset hashes and the missing-path 404 over both HTTPS address families before accepting activation. Honor the first-activation absent-state rollback and retain immutable releases afterward.

Source agents must not connect to or administer the host. A GitHub release, passing CI, or new DNS record alone does not prove that the requested site is serving the accepted bytes.
