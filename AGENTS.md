# Coup repository guidance

## Standing Dependency Completion Policy

Treat dependency remediation as part of completing authorized work on this
site, not as an optional follow-up. Proactively resolve vulnerabilities,
compatibility problems, broken installations and lockfile issues. Cover direct
and transitive dependencies, production and development dependencies,
workspaces and root-level tools. Do not dismiss findings because they are
pre-existing or development-only.

Before creating a release tag or publishing a release, require a clean locked
installation for every applicable dependency graph, zero known dependency
vulnerabilities in both full and production audits, and all applicable project
checks. An unavailable or incomplete audit is not a clean result. Use supported
upgrades, replacements or maintainable patches that preserve functionality.
Do not silence findings, weaken checks or force incompatible versions merely
to obtain a passing result.

Intermediate commits may capture coherent progress. Commit and push validated
work through this site's authorized delivery process, and complete meaningful
releases rather than stopping after reporting fixable dependency blockers.
Documentation-only housekeeping does not require an application release.

Preserve unrelated work, coordinate with other active chats, and retain existing
security, approval and production-access boundaries. Existing maintenance pauses
and repository exclusions remain in force; this policy does not expand access
or authorize otherwise excluded work. If a genuine blocker prevents completion,
preserve progress and report the exact blocker and remaining work. Distinguish
a published release from verified live deployment.

Treat this as a standing instruction for this site.

Shared Sites policy (`../AGENTS.md` when available) applies. In a standalone checkout:

- Commit coherent validated increments frequently and push completed work to `main`. Group deployable changes into meaningful milestones with a new immutable annotated tag and verified GitHub release, then follow protected deployment through read-only public acceptance checks or report the exact remaining blocker.
- Never SSH, SCP, SFTP, tunnel to, configure access to, or administer production. Protected server automation owns activation. Source push and release do not prove custom-domain publication.
- Preserve all existing A and AAAA records. DNS or external infrastructure mutations require explicit authorization for exact records and effects.
- Preserve the frozen study input/output bytes. The active 10 October study is bound by manifests; archived drafts are not research evidence. New studies need separate frozen plans, panels, independent source review, and updated claims.
- `dist/` is the complete static site. It may contain the reviewed filtering script but no writable state, application process, credentials, or control manifest. Keep `security/` outside the public root.
- Before delivery run `python3 -B -m unittest -v test_coup_simulator test_extensive_rules test_research_strategies test_research_statistics test_strategy_research test_analyze_strategy_research test_verify_strategy_research test_site scripts.test_release_artifact`, `python3 -B verify_strategy_research.py`, and `python3 -I -B check_site.py`. Build and verify release assets from a clean committed checkout. The checker must reject optimized Python, changed evidence, inventory drift, and symlinks.
- The expanded study lives in `research_results/2026-10-12-v2/`; `2026-10-12/` preserves a protocol rejected before any outcomes. Execution source fingerprints and staged plans freeze before outcomes. Resume only exact matching plans and source; cached summaries must reconcile with raw outcomes before selection. No retuning on confirmation results. Preserve all stages and raw compressed outcomes.
- `security/approved-publication.json` is the reviewed publication anchor. Do not automatically rewrite it to accept a failing check. Review exact research source, outcomes, claims, browser behavior, and all publication bytes before rotating it.
- GitGuardian service/quota/auth failure alone does not block delivery. Review outgoing files with another local secret check, preserve other hooks, and stop on real secret findings.
