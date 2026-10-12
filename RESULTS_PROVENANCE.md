# Results provenance

The active study is the validated 10 October 2026 snapshot recorded in `study_manifest.json`, `confirmation/study_manifest.json`, and `confirmation_plan.json`. It contains 88,000 screening and 168,000 held-out confirmation games. Hashes bind each panel to the simulator, runner, tests, raw outcomes, and summaries. `analyze_results.py` checks the frozen selection plan and recomputes findings.

An intervening uncommitted draft claimed newer corrected results but regressed truthful-claim resolution, block challenges, one-influence exchange, and focal identity attribution. The complete inspected draft is preserved byte-for-byte in `archive/unvalidated-regression-draft-2026-10-11/`, with `snapshot-sha256.json`. Its benchmark outputs are invalid for strategy inference and are excluded from the published site. The active files were restored from validated commit `880fa13` on 12 October 2026.
