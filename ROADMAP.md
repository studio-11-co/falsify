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
  and all rejecting all 20 reject vectors.
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

## Open defect — LLM-judged metrics are under-specified (found 2026-08-29)

§5.2 tells a verifier to "execute the evaluation using the manifest's `metric`,
`metric_args`, `seed`, and dataset". That assumes the manifest determines the
computation. For LLM-as-judge metrics — the fastest-growing class, and the whole
basis of RAG evaluation libraries — the assumption fails twice:

1. **The judge is not a named field.** `model` is defined as "the model under test";
   the *judge* model has no key. It can be carried in `metric_args`, which is
   free-form and is inside the hash — but nothing requires it, no verifier can
   detect its absence, and two hosts will name the key differently. The bar is
   expressible and not specified, which is the worst of both: no interoperability
   and no detectability.
2. **`seed` does not confer determinism** when the scoring function is a remote
   model. A seed pins a local RNG, not a hosted judge.

Consequence: a manifest can be locked, timestamped and verified TAMPER-FREE while
the bar it encodes is under-determined. Re-run with a different judge, the verdict
changes, and nothing in the record shows it. This is not in the §8.1 threat model,
which lists four other non-protections.

Practice already prescribes the fix, and from two independent directions. RAG evaluation
guidance tells practitioners to "fix the judge model per experiment" and names "comparing
scores across different judge models" as a common pitfall. A separate practitioner handbook,
in a section titled "Statistical comparison and release gates", is sharper: under **Judge
calibration** it says "measure agreement against human labels; freeze prompt/model/version;
include examples; periodically re-audit drift", and under **Release rule** it requires "no
critical-slice regression, statistically credible aggregate improvement, and SLO/security
compliance". So the requirement exists in the field, stated as a release gate; what is
missing is a named place to record it and a verifier that notices when it is absent.

Two consequences for the field design, both from that wording:

1. The unit to pin is **prompt + model + version**, not the model alone. The first sketch of
   this defect said "the judge model", which is too coarse.
2. **A hosted judge can change while its name stays the same.** Recording a model name pins a
   label, not a function — which is why the same handbook asks for periodic drift re-audits.
   A field carrying only a name would give false assurance: the manifest would verify while
   the bar quietly moved. Any resolution has to say what is actually being committed to — a
   prompt hash and a provider-attested version at minimum — and be honest that where a
   provider offers no immutable identifier, the judge cannot be pinned at all. That
   limitation belongs in the threat model, not in the marketing.

Candidate resolution for v1.0 (not decided): a reserved `metric_args.judge` mapping
(`id`, `version`/`hash`, `prompt_hash`, `temperature`), plus a conformance rule that
a metric declared as judge-dependent MUST carry it. Needs a decision on how a
verifier learns a metric is judge-dependent without a metric registry.

⚠ Scope: this is a limitation of our own specification, found by reading a host
framework's documentation. It does not mean any published manifest is wrong; it
means the format does not yet stop this class of under-specification.


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
