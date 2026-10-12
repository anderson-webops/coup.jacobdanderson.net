# Preserved pre-execution protocol

Commit `c6b6d2c` froze this plan before outcomes. The first launch stopped at the
global-plan comparison because a Python tuple in `stress_pools` serialized as
a JSON array but was compared to the tuple on reload. No stage was created and
no games were generated. This plan is retained exactly as written.

The serialization fix normalizes JSON representation before comparison. The
separately frozen executed study is in `../2026-10-12-v2/`. Its policy parameters,
sampling budget, seed formula, and selection procedure retain the preregistered
design; execution source fingerprints record the correction. This directory
contains no outcome evidence and is excluded from the public research bundle.
