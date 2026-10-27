# Expansion validation

This is a local candidate from source HEAD `34e8bfc2a5edbfb3dc2425f36ae90afbbeec4ccc`. No source commit, push, tag, release, publication or production change was made. The earlier local editorial work was preserved and incorporated.

## Scientific evidence

- Three rules options, 2–10 players, eight screened strategies and five opponent fields.
- 1,908,576 scheduled games, including 1,620,000 fresh confirmation games. All 17,960 capped games remain in every rate denominator.
- Independent reconstruction reconciled every outcome across 1,410 jobs. All 25,380 sampled strict replays matched saved winners and turn counts.
- The eight expansion execution files and ten preserved base execution files still match their frozen fingerprints. The base outcome audit also passed. No strategy or inference settings changed after outcomes.
- The protocol is a local hashed source and plan snapshot, without an independent timestamp registry. Only two screening-selected finalists per rules/player setting receive primary confirmation.

The [interpretation](EXPANSION_FINDINGS.md), [protocol](EXPANSION_STUDY.md), [rules review](EXPANSION_RULES.md) and [raw evidence](../research_results/2026-10-18-expansion/) record the methods and limits.

## Automated and browser checks

All **241 distinct automated tests** passed. The initial full regression ran 238 tests; the publication suite then grew from 13 to 16 tests after an independently found path-containment issue was fixed. Its 16 tests passed afterward. These counts overlap. The 20 site and release-artifact tests were additionally rerun against the completed, locally reviewed 34-file candidate and all passed. Release tests use isolated synthetic source fixtures; no application release was created.

The isolated `python3 -I -B check_site.py` check passed. Publication validation rejects changed evidence, source drift, unexpected files, symlinks, optimized Python, escaping inputs, invalid archive members, wrong raw seed coordinates and rehashed false statistical claims. The existing 128 MiB publication limit remains intact.

The actual page passed **270** rules/player/field/evidence combinations, including **61** panels with tied win counts. Displayed main results, broad averages, weak fields, counter rates and comparison directions matched the saved data. The review covered 360, 390, 768 and 1440 pixel widths, three captioned expansion tables, labeled selectors, keyboard order, visible focus and disclosure controls, with no page overflow or browser errors. Earlier base modes remained functional. This records rendering and basic accessibility checks, not a complete WCAG audit. Small table-heading contrast improved from 4.29:1 to 5.09:1.

A separate disposable UI fixture exercised exact broad ties, reversed supported comparisons and approximate-only differences. It never entered the research directory or public site. A desktop full-page capture was refreshed after a resize capture artifact; the settled desktop and phone captures are retained in local diagnostics.

## Preservation and publication boundary

All 25 earlier public evidence files and every earlier embedded study-data member are byte/value equivalent to the preserved editorial candidate. Its four initial local files were copied before integration. Among the earlier public files, only the homepage, stylesheet and publication metadata changed; five new expansion evidence assets were added. The reviewed static tree has **34 files, 61,470,319 bytes**. Controls remain outside `dist/`; the page uses the two exact hashed script blocks and no remote requests or writable state.

HEAD and the initially empty staging area are unchanged. Source, outcomes and generated-site changes remain local. The own automated browser and disposable fixture server were closed. A loopback-only preview of `dist/` remains available at [the local preview](http://127.0.0.1:8867/?rules=combined) for review.

Exact counts and hashes are in the [validation receipt](validation/2026-10-18-expansion-local.json). Diagnostic logs, snapshots and captures are indexed under `.ai-work/runs/20261018-expansion/`.
