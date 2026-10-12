# Frozen analysis across Python versions

The original study ran under CPython 3.9.6. The expanded 122-test suite passed
both locally and in Linux CI at source `5687d034`. CI then passed all raw-data,
source, manifest, schedule and selection checks, but failed the frozen analyzer's
exact comparison of recomputed floating-point values with saved findings.

Independent CPython 3.12 and 3.14 audits reproduced the issue: 283 derived floats
differed, with a maximum absolute difference of `3.469446951953614e-16`.
Every count, directly divided rate, flag, identity, source hash, type and
descriptive ranking matched. CPython 3.12 changed floating-point summation to a
more accurate algorithm, as documented in the [Python documentation](https://docs.python.org/3.12/library/functions.html#sum).
Statistical math functions can also have platform rounding differences.

The portable delivery verifier is `verify_strategy_research.py`. It calls the
unchanged frozen analyzer with `write=False`, retaining every raw-outcome audit.
It requires exact structure, order, scalar types, counts, direct rates, inference
flags, selections and hashes. Only the following finite derived floats may
differ by at most `1e-14` absolute, with no relative tolerance:

- Paired `difference`, normal interval endpoints and conservative interval
  endpoints within confirmation, counter and ablation families.
- Equal-field and alternative-weight scenario means.

Signs and descriptive candidate ranking orders must remain exact. Other numeric
leaves, including mean turns and individual win rates, remain exact. The verifier
returns the saved canonical findings after checking them, rather than rewriting
the evidence or rerunning candidate selection.

Two one-decimal percentage displays sit at rounding ties: six-player mixed
Exchange versus baseline and six-player card-balanced opponents. Recomputed
last-bit differences render these as `+2.1%` and `+1.8%` instead of the frozen
`+2.0%` and `+1.7%`. Their unrounded values differ only at machine precision;
interval support and practical-threshold flags do not change. The saved JSON
must keep its canonical encoding, and saved Markdown must exactly equal the
frozen renderer applied to that verified saved JSON. The publication checker
separately pins the exact approved JSON, Markdown bundle and all other served
file hashes. No frozen execution source, study output or public byte was changed.

Eleven additional delivery regression tests reject changed types, discrete
results, unlisted float changes, changed signs, excessive numeric drift,
nonfinite values, reordered or changed structures, duplicate JSON keys,
noncanonical saved encoding, changed descriptive rankings and altered Markdown.
The required delivery suite now has 133 methods: the preserved 122-method suite
plus these eleven compatibility tests.
