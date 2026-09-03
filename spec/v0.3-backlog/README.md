# PRML v0.3 — backlog

This directory tracks RFC issues deferred from v0.2 to v0.3. Each file is a
proposal skeleton: problem statement, current v0.2 position, proposed v0.3
direction, open questions. Each will be mirrored as a GitHub issue with
label `rfc-v0.3` on `studio-11-co/falsify` when the v0.3 comment window opens.

**v0.3 comment window:** not yet scheduled. Provisional target Q4 2026.

## Files

- `01-claim-tree.md` — multi-metric suite manifests (HELM, Big-Bench, LMSYS Arena, LiveCodeBench)
- `02-producer-struct.md` — structured producer with key_id and signature
- `03-tolerance.md` — GPU floating-point non-determinism, epsilon bands
- `04-identity-levels.md` — Level 0–4 documentation (lives in cookbook first, normative reference in v0.3)

These four are the binding decisions from the v0.2 freeze (2026-05-22).
Other deferred items remain in the v0.2 RFC "Proposals deferred to v0.3+"
list and may or may not promote to this backlog depending on community
input received after freeze.
- `05-sealed-disclosure.md` — sealed commitments and field-level selective disclosure (opened 2026-09-03; registry sealed commits exist today, spec unchanged)
