# v0.3 RFC issue: identity levels

**Status:** Deferred from v0.2 freeze (2026-05-22). Open for v0.3 design.
**Tracking:** to be mirrored as `rfc-v0.3` issue on `studio-11-co/falsify`.

## Problem

A verifier reading `producer: falsify.dev` cannot tell how strongly that
string is bound to the real-world entity that authored the manifest. A
manifest anchored via a Sigstore certificate and a manifest whose producer
string was typed into a YAML file by hand look identical to a registry.
The v0.1 optional `signature` field addresses binding for producers who
choose to sign; nothing in the spec signals binding *strength*.

## v0.2 position

Non-normative. The cookbook documents a five-level ladder in
`falsify-cookbook/IDENTITY-LEVELS.md` (published 2026-05-19):

- **Level 0**: unsigned local manifest (bare producer string, no anchor)
- **Level 1**: public git commit or registry timestamp
- **Level 2**: signed commit or detached PGP / minisign signature over the
  canonical bytes (stored in the `.prml.sig` sidecar)
- **Level 3**: Sigstore keyless signing + Rekor transparency-log entry
- **Level 4**: institutional / regulated identity (HSM-managed key,
  registry-enforced)

PRML v0.1 and v0.2 accept any level; the spec never refuses an unsigned
manifest. The machinery for Levels 0 to 2 exists today (v0.1 §2.3.3
optional `signature`); the normative `.prml.sig` sidecar adoption and the
structured producer object that Levels 2+ presuppose are re-targeted to
the v0.3 cycle (see the v0.1 errata dated 2026-07-11). In practice most
published manifests sit at Level 0 or 1.

## Proposed v0.3 direction

A self-declared `identity_level` field with integer values 0 to 4 matching
the cookbook ladder. Informative even when present: verifiers retain the
obligation to independently confirm the claimed level from the evidence
they can check (signature, Rekor entry, registry receipt). Depends on
issue 02 (structured producer).

## Open questions

- **Self-declared vs derived.** Should `identity_level` be a field inside
  the canonical bytes, or a property a verifier derives from checkable
  evidence and never trusts as declared?
- **Overclaim semantics.** If the field is hashed, a producer claiming
  Level 3 without a Rekor entry has lied inside signed bytes. Is that a
  feature (an auditable overclaim) or a trap for honest mistakes?
- **Level 4 scope.** Does institutional identity belong in the spec, or is
  it registry policy layered on top?
- **Collapse into issue 02.** Should the level be a computed view over the
  structured producer object rather than a separate field?

## Workarounds available today (v0.1/v0.2)

- Place a manifest on the ladder manually using the cookbook document and
  state the assessment in accompanying documentation.
- Producers who need Level 2 or 3 binding now can sign the canonical bytes
  (v0.1 §2.3.3) or run cookbook Pattern 11 (Sigstore); verifiers check the
  evidence directly rather than a declared level.
