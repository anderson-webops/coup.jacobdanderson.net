# Independent replay audit for the 12 October Coup study

`scripts/audit_research_replay.py` checks the seven new research panels after
the frozen runner has finished. It does not import the runner, call its job
function, use its roster or seed helpers, or accept its summary statistics as
proof of individual games. It reads the global and stage plans, verifies their
SHA-256 links and the declared execution-source hashes, then checks every
stage's inventory against its manifest. A changed plan, source file, raw file,
diagnostic, or summary stops the audit.

The execution directory is `research_results/2026-10-12-v2`. The earlier
`2026-10-12` directory records a preregistration attempt that stopped before
any games; it remains preserved separately.

For **every raw job**, the audit reconstructs the candidate and opponent
identities from the saved plan. Identity zero is the focal candidate. A
rotation assigns identity `i` to physical seat `(i + rotation) % players`.
The audit independently computes each game's seed from the plan's stage
namespace, player count, field index, and block. It verifies the coordinates,
seed, focal seat, winner flags, and row count of every raw row without using
job summaries. It then replays the first, midpoint, and last block of each job
at every physical seat. Cyclic mixed or stress fields also replay the first
block with reversed opponent order. Each replay uses the frozen `ResearchGame`
implementation with checks after every action, and compares the winning seat
and turn count with the stored raw row. The audit computes the winning
**identity** using its own rotation map and binds the replayed outcomes into
each stage's digest.

The global plan must explicitly contain `stress_pools` for `assault`,
`economy`, `chaos`, and `alternating`. The original runner's Python roster
constants are insufficient independent audit evidence. The audit fails if a
needed pool is absent from the plan.

From the repository root, a complete audit is:

```sh
python3 -B scripts/audit_research_replay.py
```

This writes `research_results/2026-10-12-v2/replay-audit.json` only after all
seven stages pass. The receipt includes the execution source hashes, the
global and stage plan hashes, stage manifest hashes, job and raw game counts,
replayed game counts, the audit script hash, and replay identity-outcome
digests. An existing, different receipt is preserved and causes a failure.

While later stages are still running, a completed tuning panel can be checked
without writing a receipt:

```sh
python3 -B scripts/audit_research_replay.py --stages tuning
```

This is a deterministic spot replay, not a full second simulation of every
game. The stage manifest and all raw-row coordinate checks cover the complete
recorded dataset; the per-game outcome comparison covers the stated sample.
The audit cannot independently prove the correctness of the shared Coup rules
engine, so its rule-transition tests remain a separate gate. It also cannot
establish that the modeled opponent population represents human players.
