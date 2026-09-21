# v0.3 RFC issue: the action envelope — what the system under test was allowed to do

**Status:** backlog, opened 2026-09-15. **Source: outside, and it is a reading rather than a
request.** Prompted by Mikkilineni, *From Sandbox Escape to Authority Failure* (14 Sep 2026), a
review of the July 2026 OpenAI–Hugging Face agent incident. That paper does not mention PRML and
does not propose a pre-run record; its own proposal is a runtime governor. The connection below is
ours, not the author's, and should not be attributed to him.

## Problem

PRML v0.1 fixes the **bar**: metric, comparator, threshold, dataset identity, seed. For a
benchmark run that is the whole measurement contract, because the only thing that varies between
runs is the model.

For an **agentic evaluation** it is not. What the system under test was *permitted to do* during
the run — which tools, which network egress, which credentials, which third-party effects — is as
determinative of the result as the threshold. A pass at 0.85 means nothing if one run had network
access and the next did not, or if the boundary was decided after the interesting behaviour
appeared.

The review puts the same point from the safety side:

> *"'sandbox' should be specified as more than a virtualized compute boundary. The evaluation must
> include a **declared external commitment surface**: which writes, messages, egress destinations,
> credentials, and third-party effects are allowed."*

Declared, in advance, and machine-enforceable. That is the same class of object PRML already
exists to fix in time — just a different field.

## Why this is not scope creep

PRML already carries a slot of exactly this shape. From the v0.1 schema:

> `compute_envelope` — *"Optional structured description of compute conditions (precision, hardware
> class, software stack hash). **Out of scope for verdict computation in v0.1.**"*

So the precedent is established: a declaration of **run conditions**, inside the canonical bytes
and therefore inside the hash, but deliberately **not** verdict-bearing. An action envelope is the
agentic analogue of the same idea. It does not enter the comparator, it does not change PASS or
FAIL, and it does not make PRML a policy engine. It records what the run was allowed to do, so a
later reader can tell whether two results are comparable at all.

## Sketch, not a design

```yaml
action_envelope:
  tools: [python, http_get]
  network: none          # none | allowlist | open
  network_allowlist: []  # required and non-empty when network is allowlist
  credentials: none      # none | scoped | broad
  third_party_effects: false
  max_steps: 50
```

Open, deliberately: whether this is a free-form object like `compute_envelope`
(`additionalProperties: true`, no conformance burden) or a constrained vocabulary that four
implementations must agree on byte-for-byte.

## Open questions

- **Free-form or constrained?** Free-form costs nothing and buys nothing enforceable: two producers
  would describe the same envelope differently and the hashes would differ for no real reason.
  Constrained means a vocabulary this project would have to maintain for agent capabilities, which
  change faster than any spec cycle. `compute_envelope` chose free-form and has, as far as we know,
  never been used by anyone.
- **Does declaring it prove anything?** No, and the limit is the same as everywhere else in PRML: a
  declared envelope fixes what the producer *said* was permitted, not what was enforced. The review
  is explicit that enforcement is a runtime property surviving executor compromise, which a record
  cannot supply. Any wording must not imply otherwise.
- **Is the demand real?** There is no external request for this. `compute_envelope` is the honest
  precedent in both directions: it shows the pattern is legitimate, and it shows a slot like this
  can sit unused in a shipped spec for a year. Nothing here should be built before someone running
  agentic evaluations asks for it.

## Related

- v0.1 schema, `compute_envelope` — the precedent, and the cautionary example
- `07-framework-profile.md` — the other outside-sourced backlog item from the same week
- Mikkilineni, *From Sandbox Escape to Authority Failure*, 14 Sep 2026, §13; triage record in
  GAP-EVIDENCE §DJ-5
- Steel, *Attaching liability to agentic identity* (CISES/ETRP policy brief, 14 Sep 2026) — a second,
  independent source on the same July 2026 incident, framing the fix as a **permissions record**:
  "the scope an agent is granted and the actions it takes are logged against its identifier, so that
  after an incident the question of who authorised what is answered by the record." Same object as
  the envelope above (what was *permitted*), reached from the liability side. Neither paper mentions
  PRML; the connection is ours. Triage record in GAP-EVIDENCE §DK.
- Commonwealth of Australia, *Agentic AI Harnesses — the layer above the model* (Sep 2026, national
  cyber-security guidance) — a third source, this time a government one, that names the same layer:
  "the harness determines which tools are available, enforces permissions and guardrails, and executes
  approved actions", and asks organisations to "record prompts, responses, tool invocations, approvals,
  actions". That is the vocabulary an envelope field would have to match if it is ever built. Runtime
  and logging only; no pre-run commitment, no mention of PRML. Triage in GAP-EVIDENCE §DK.

- Kara, Z., *Improving Frontier AI Incident Reporting Regimes* (GovAI policy brief, Sep 2026) — recommends that
  agent action logs be tamper-proof ("subsequent changes or deletions are detectable"), keyed by a per-instance
  identifier with timestamps, model version and operating environment, so that a later investigator can attribute
  an action. Same evidentiary shape as the action envelope; it does not address evaluation criteria or pre-run
  commitment.