# Coup publication contract

The deployable website is the tracked `dist/` tree. It is served as static files with no site process, database, account, or writable application state. The simulator and raw study data are downloads within that static tree. The source repository, a GitHub release, and the live custom domain are separate states.

## Source and release checks

Run the simulator tests and the publication checker before source delivery:

```sh
python3 -B -m unittest -v test_coup_simulator test_extensive_rules test_research_strategies test_research_statistics test_strategy_research test_analyze_strategy_research test_site scripts.test_release_artifact
python3 -B analyze_strategy_research.py --verify-only
python3 -I -B check_site.py --root .
```

The site checker validates the complete `dist/` inventory against `security/approved-publication.json`. That independently reviewed anchor records each public file hash, size, and media type. It must be updated only after the exact source evidence, displayed claims, downloadable study files, and browser policy are reviewed. `security/site-policy.json` records the required response headers, including the approved inline-script hashes in Content Security Policy. The versioned `deployment-contract.json` declares static hosting and protected host capabilities. None of these three control files belongs inside the public tree.

After the source is committed and the checkout is clean, build and verify the exact candidate under the repository's ignored `.ai-work/runs/` area. An external output directory, such as CI's `RUNNER_TEMP`, is also supported. The builder rejects output elsewhere in the tracked repository and checks that an internal output path is Git-ignored:

```sh
release_dir="$(mktemp -d .ai-work/runs/coup-release-XXXXXXXX)"
python3 -I -B scripts/release_artifact.py build --output-dir "$release_dir"
python3 -I -B scripts/release_artifact.py verify \
  --release-dir "$release_dir" \
  --expected-commit "$(git rev-parse HEAD)" \
  --expected-version "$(tr -d '\r\n' < VERSION)"
```

The three release assets are `coup-site-v<version>-<commit-prefix>.tar.gz`, `release-manifest.json`, and `SHA256SUMS`. The archive contains only `dist/` files. The release manifest carries the full source commit, reviewed research-source hashes, archive and public-file digests, exact deployment contract and response policy, and hashes of the independently reviewed control files. The verifier rejects changed source controls, unexpected or linked archive members, size and hash drift, path traversal, and a wrong version or source commit. It checks the extracted tree with the same site checker used on source.

The repository workflow validates source and builds a candidate on pull requests and pushes to `main`. It retains the candidate as a short-lived CI artifact. A release-worthy change should use an annotated `v<version>` tag at the exact validated commit and publish the verified candidate bytes as an immutable GitHub release. A CI artifact or GitHub release establishes source and artifact readiness only.

## Protected host onboarding

The protected server automation must independently recognize the canonical repository, annotated tag, commit, archive digest, deployment contract version, and minimum host capabilities before staging or activating a release. It must verify the exact public-file inventory and apply the separately reviewed response policy, including the hash-approved inline script in CSP, without running scripts from the candidate repository. The host retains DNS, TLS, Nginx configuration, file ownership, release pointers, and deployment credentials under its own control.

The new custom domain requires protected host onboarding and both IPv4 and IPv6 DNS records. After immutable staging, the host should compare the served `/` response with the release manifest's `dist/index.html` digest, verify other public assets and response headers over IPv4 and IPv6, and require a real 404 for the missing probe path. It should promote atomically. For the first activation, failed acceptance restores the prior absent state. After the first successful activation, the host retains the prior immutable release and its policy for rollback. There are no migrations or application writable paths. A missing host capability must leave the serving state unchanged and be reported as an onboarding requirement.

Source workspace agents do not connect to or administer the production host. Source delivery or a published release does not establish that `coup.jacobdanderson.net` is serving the new content. Verify the exact live bytes and both address families separately after protected activation.
