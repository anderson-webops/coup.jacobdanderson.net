# Coup expansion study

## Frozen protocol

This study is separate from the preserved base-game studies. Its inputs and
outputs belong in `research_results/2026-10-18-expansion/`. The protocol was
locally frozen before outcomes at `2026-10-19T01:33:51.633353+00:00`, which was
18 October in the project owner's time zone. A local hash and source snapshot
provide reproducibility evidence; they are not an independently timestamped
registration.

The frozen `plan.json` SHA-256 is
`a76f7d94f3a4db07ff08f3cbfe7aa6c4f6032ede0b25a3c8ff0c61b82e8b172e`.
`preregistration.json` binds that plan and the eight source fingerprints. The
`sources/` directory preserves exact copies of the engine, policies, runner,
statistics, independent auditor and their tests. Subsequent work must preserve
these bytes. An execution change requires a separate study and plan.

The [rules review](EXPANSION_RULES.md) records sources, interpretations and
simulation conventions. The three independently analyzed profiles are:

| Profile ID | Rules option | Role replacing Ambassador | Allegiances and reserve |
| --- | --- | --- | --- |
| `inquisitor` | Inquisitor only | Inquisitor | Absent |
| `reformation` | Allegiances + Ambassador | Ambassador remains | Present |
| `combined` | Allegiances + Inquisitor | Inquisitor | Present |

Every profile is tested at each player count from two through ten. The deck
uses three copies of each role for two through six players, four for seven or
eight, and five for nine or ten. In a two-player game, the first player begins
with one coin. Focal participant identity is distinct from its policy name and
rotates through every seat, including when several participants use the same
policy.

## Policies and opponent fields

Eight fixed policy configurations enter screening:

| Policy ID | Display name | Main preference |
| --- | --- | --- |
| `honest` | Truthful economy | Held-role actions, impossible-claim challenges and truthful reserve collection |
| `bluff` | Tax bluffer | Tax on non-Coup turns and every legal block, including bluffs |
| `skeptic` | Always challenge | Challenges every role claim while usually making held-role action claims |
| `treasury` | Treasury seeker | Larger reserve withdrawals, selective challenges and some bluffs |
| `shield` | Defensive conversion | Reducing visible threats through conversion and defensive card retention |
| `converter` | Active conversion | More conversion weight when it reduces immediate threats |
| `information` | Information seeker | Exchanges, examination and valid private inspection knowledge |
| `balanced` | Balanced | Reserve income, conversion, card retention, examination and selective challenges |

These descriptions identify preferences, not exclusive action rules or human
probabilities. The exact configurations and decisions are in the frozen
`expansion_policies.py`. For example, the two policies that usually Coup at
eight coins still obey compulsory Coup at ten. Information affects card
retention and action scoring; conversion preferences do not create conversion
actions in the Inquisitor-only profile.

Selective challengers combine an unseen-card prior with public claim history
and any still-valid private examination. Policies receive their own hidden
cards, public information and permitted private inspections. They do not
receive other hidden hands or deck order. Participant decision randomness is
separate from environment randomness. Behavior is reset for every game.

Five fields are analyzed separately:

| Field ID | Opponents |
| --- | --- |
| `honest` | Copies of Truthful economy |
| `bluffing` | Copies of Tax bluffer |
| `skeptical` | Copies of Always challenge |
| `adaptive` | Copies of Balanced |
| `mixed` | A predetermined cycle through all eight policies |

The `adaptive` identifier names the Balanced field. It does not mean training
between games. The mixed field cycles through policy IDs by block and reverses
the opponent order on alternating complete pool cycles. At a given player
count, every candidate faces the same planned composition and seed coordinates.

## Stages and selection

| Stage | Independent complete rotation blocks per job | Jobs | Scheduled games |
| --- | ---: | ---: | ---: |
| Screening | 32 | 1,080 | 207,360 |
| Confirmation | 1,000 | 270 | 1,620,000 |
| Counter search | 32 | 48 | 9,216 |
| Counter confirmation | 1,000 | 12 | 72,000 |
| Total | | 1,410 | 1,908,576 |

Screening measures all eight policies against all five fields in each
profile/player setting. The two highest equally weighted field averages advance
to confirmation; ties use the lexical policy ID. Equal denominators permit
selection with integer win counts. These two finalists are fixed before fresh
confirmation outcomes. The study does not confirm all eight policies.

Targeted counter work covers Inquisitor-only games at two and six players,
Allegiances + Ambassador at four and ten, and Allegiances + Inquisitor at four
and ten. In each setting, the screening leader becomes the target. All eight
policies face copies of that target on separate search blocks. The strongest
non-target policy advances, with lexical tie breaking. Fresh counter
confirmation compares it with target self-play on matched blocks. Search
results do not count as confirmation.

Each seed is the big-endian integer representation of SHA-256 over the ASCII
coordinate `coup-expansion-study-v1:profile:stage:players:field:block`. Stage,
profile, player count and field therefore have separate deterministic
namespaces. Each block contains every focal seat rotation. Candidate pairs
share block seeds and seat identities. Rotations within a block are treated as
related observations, rather than independent games for inference.

## Statistical interpretation

All games run with strict invariant checks after each action. A game that
reaches 1,000 actions without a winner is recorded as a capped draw. Draws remain
in every win-rate denominator. Wins divided by all scheduled games give the
reported rates.

There are 135 preregistered confirmation contrasts: one finalist pair for each
of three profiles, nine player counts and five fields. Their approximate normal
intervals use variation between paired complete rotation blocks and a
Bonferroni adjustment across the full family. Conservative simultaneous
Hoeffding bounds use the paired block range of minus one to plus one. The six
counter contrasts form their own six-comparison family. Both use a 5% family
error setting and a two-percentage-point practical threshold.

A lower bound above zero supports the stored first policy over the stored
second in that scenario. An upper bound below zero supports the second. A
lower bound above two percentage points supports a practical positive
advantage under that method. Approximate support and conservative support are
reported separately. A small numerical lead with bounds spanning zero remains
unresolved.

The confirmation field average gives each programmed field one fifth of the
weight. It is descriptive: it does not estimate a human opponent population,
and a leader of this average need not win every field. The weakest field helps
identify a policy's modeled exposure. Results compare the two selected
finalists at a specific rules option and player count, not every screened or
untested strategy. Field weighting and opponents may change the ordering.

These policy configurations change several choices together. A comparison
between Active conversion and Balanced does not isolate the causal value of
conversion. The study contains no expansion component-ablation experiment.
Negotiation, persuasion and learning between games are outside the model.
Rates from the preserved base study and this expansion study use different
decision models and opponent fields, so they should be interpreted within
their own studies.

## Independent audit and reproduction

The runner's verifier reloads every raw outcome, reconciles
summaries and stage manifests, reconstructs selections, computes comparisons,
and checks the saved findings. It refuses changed execution source, source
snapshots, plans, raw files, unexpected inventory and symlinks.

The separate `audit_expansion_research.py` does not import runner schedule,
selection or statistics helpers. It reconstructs all raw seed coordinates,
lineups, focal identities, outcome flags, aggregate counts, finalist selection
and counter selection. It also replays the first, midpoint and last complete
blocks of every job, at every physical seat. The frozen default schedule implies
25,380 checked replays across 1,410 jobs. This is a planned audit count, not a
claim that the research or replay has finished.

Each replay requests strict action checks, compares the winner and executed
turn count, then explicitly checks card, influence and coin invariants. The
auditor shares the expansion engine; the independently authored rules
transition tests provide a separate kind of rules verification. Its receipt
records source and plan hashes, stage plan and manifest hashes, counts and a
digest of replayed identity outcomes.

Run from the repository root after the study finishes:

```sh
python3 -B -m unittest -v test_expansion_simulator test_expansion_study test_expansion_audit
python3 -B expansion_study.py --output-dir research_results/2026-10-18-expansion --verify
python3 -B audit_expansion_research.py --results-dir research_results/2026-10-18-expansion --write-receipt
```

The verifier and independent audit reject optimized Python. The auditor writes
a full receipt only after all four stages pass, and refuses to overwrite a
different existing receipt. While later stages are running, a read-only audit
of completed prefixes is available, for example:

```sh
python3 -B audit_expansion_research.py --results-dir research_results/2026-10-18-expansion --stages screening
```

To reproduce the frozen protocol, use the exact source snapshots and the same
plan. `expansion_study.py` resumes an exact matching study, refuses changed
counts or source, and reconciles every cached job with its raw outcomes before
reusing it. Do not alter an existing plan to resume changed execution code or
select strategies using confirmation outcomes.
