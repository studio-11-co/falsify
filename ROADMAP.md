# Roadmap

Last rewritten: 2026-07-11, for the v0.3.10 corrections release. The
previous version of this file described a "Next: CLI v0.2.0" that shipped
long ago and repeated promises the frozen v0.2 RFC does not make. This
version states where things actually are.

This roadmap is directional, not a commitment. Items move as hosts and
reviewers actually appear, not on a calendar.

## Strategy

PRML is an embedded pre-commitment primitive, not a standalone standard
push. The bet is that eval and runtime hosts adopt "lock the bar before
the run" as a feature inside tools people already use. The adapters are
the product surface:

- `mlflow-falsify` (MLflow plugin)
- `falsify-inspect` (Inspect AI adapter)
- `falsify-giskard` (Giskard adapter)
- `examples/deepeval/` (runnable DeepEval integration example)

A PRML manifest proves the bar was locked before the run. It never proves
the result.

## Now (v0.3.10, about to release)

- Current CLI version: 0.3.10, a corrections release. No behaviour change
  to canonicalization; no valid existing hash changes. See CHANGELOG.md
  for the itemized registry and documentation corrections.
- Four reference implementations (Python, JavaScript, Go, Rust), all
  byte-equivalent on the 21 frozen conformance vectors (13 v0.1 + 8 v0.2)
  and all rejecting the 14-vector reject suite.
- Registry (`registry.falsify.dev`): Ed25519-signed receipts, PRML
  validation at commit time, full-manifest storage, in-browser verifier
  running the same canonical.js the server uses.
- MCP verdict-log server (`mcp_server/`) and the Managed Agents
  verdict-refresher (`managed_agents/`) remain available as shipped.

## Next

- Ship v0.3.10 and sweep every surface (PyPI, npm, spec site, registry).
- External timestamp anchoring for the registry: SHIPPED 2026-07-12.
  Every receipt is RFC 3161 countersigned (timestamp.sigstore.dev, raw token
  at /<hash>.tsr) and full-manifest records are mirrored to the Rekor v2
  transparency log (inclusion proof at /<hash>.rekor). Remaining option on
  this track: eIDAS qualified electronic timestamps (a QTSP-issued RFC 3161
  token with the Article 41 legal presumption) as a configurable TSA for
  regulated deployments; the endpoint is already configuration, not code.
- Suite manifests (claim tree, leaves_total): priority RAISED 2026-07-16
  after independent external review converged on the same multiplicity gap
  (pre-register N variants, publish only the winner). Still gated on named
  external reviewers per the Lock #2 postmortem commitments.
- Spec v0.2.0 stays a frozen RFC. Promotion to final is deferred until
  external reviewers exist, per the Lock #2 postmortem commitments: named
  reviewers on record, outreach before any lock, and a 90-day window. The
  three open questions (P-01, P-02, P-03) will not be resolved
  unilaterally.

## Soon (spec v0.3 themes, deferred)

The CLI has been on the 0.3.x line since v0.3.0 (2026-05-30); the spec
v0.3 cycle is a separate track and has not opened. Its themes are written
up in `spec/v0.3-backlog/`:

- Claim tree / multi-metric suite manifests (`01-claim-tree.md`)
- Structured producer with key_id and signature (`02-producer-struct.md`)
- Tolerance for GPU nondeterminism (`03-tolerance.md`)
- Identity levels 0 to 4 (`04-identity-levels.md`)

The v0.3 comment window opens when a host integration or a reviewer pool
exists, not before. Earlier drafts of this file named a target quarter;
that date was invented and is withdrawn.

## Later (speculative, only if adoption warrants)

- VS Code / JetBrains inline verdict status.
- Federated verdict registry, opt-in and privacy-preserving.
- Agent integration: agents author specs and run `falsify lock` before
  acting on a claim.

## What won't ship (non-goals)

- Not a statistics package. The spec declares the threshold; the tool
  enforces it.
- Not an experiment orchestrator. One command per spec.
- Not a secrets manager. Specs must not embed keys.
- Not a compliance product. PRML is a primitive that makes named
  regulatory obligations satisfiable; it sells no audit service.

## Discipline

Deterministic exit codes, canonical hashing, standard-library-only runtime
where possible. Feature creep dilutes the trust the tool sells. Small,
deterministic, verifiable.
