# Snapshot and change lifecycle

Every semantic-extraction attempt is stored. A result becomes `accepted` only when it
is complete and passes deterministic schema/evidence checks, including known evidence
IDs and evidence for every found value. Review-required, conflicting, or invalid
attempts remain candidates and never replace the last accepted snapshot.

Comparison uses the preceding accepted snapshot for the same bank, family, and stable
offering. Canonical payloads preserve business values, states, bounds, currencies,
units, and conditions while excluding timestamps, citation ordering, prose formatting,
and evidence locations. The first accepted observation has no field changes. Equal
canonical values with changed evidence create `snapshot.provenance_changed`, not a
tariff change.

Publication is atomic per offering: knowledge versions/chunks, extraction attempt,
snapshot decision, changes, manifest, offering status, and audit event commit together.
Rollback preserves the prior index and accepted snapshot.
