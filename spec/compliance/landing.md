# EU AI Act compliance — PRML v0.1

**For:** compliance leads, AI governance officers, notified body assessors, quality management auditors.

**Status:** Working draft v0.1 under public review. Not a product. Not a service. A specification and a reference implementation, both under permissive licenses.

> **v0.1 scope limit — read before citing this for Annex III.** PRML makes a *committed* evaluation claim tamper-evident. On its own it does **not** prevent the two adversaries most relevant to a high-risk audit: *selective publication* (publish only the claims that passed) and *back-dating* (author a manifest after the fact). A v0.1 deployment used as Article 12 evidence **MUST** add one of three deployment-level mitigations — a publish-before-run anchor, sequential `claim_id` allocation, or an external pre-registration anchor (see [spec §8.1](https://spec.falsify.dev/v0.1#threat-model)). Without one of them, a v0.1 manifest is **not** suitable for standalone Annex III evidence submission, and the producer should declare so.

---

## The deadline that started this

The EU AI Act (Regulation 2024/1689) entered force on 1 August 2024. The high-risk obligations apply on **2 December 2027** (deferred from 2 August 2026 by the EU Digital Omnibus).

By that date, providers of high-risk AI systems (Annex III) must demonstrate, with documented evidence:

- **Article 12** — automatic logging of evaluation events relevant to risk identification, retained over the system's full lifetime.
- **Article 17** — a quality management system with documented evaluation procedures and outcomes.
- **Article 18** — ten-year retention of technical documentation.
- **Article 50** — transparency obligations to deployers of general-purpose AI systems.
- **Article 72** — a post-market monitoring plan with documented review intervals.
- **Article 73** — reporting of serious incidents with traceable cause analysis.

Penalties under **Article 99**: up to **€15M or 3% of global turnover** for non-compliance with the high-risk regime. Up to **€7.5M or 1%** for incorrect information supplied to authorities.

The mapping above is also satisfied, in adapted form, by:

- **NIST AI RMF v1.0** — Govern, Measure, and Manage functions.
- **ISO/IEC 42001:2023** — clauses 7.5 (documented information), 8.4 (operational planning), 9.2 (internal audit).
- **Colorado AI Act SB24-205** — algorithmic discrimination assessments (effective 1 February 2026).
- **Korea AI Basic Act** — provider obligations (effective 22 January 2026).

---

## What is unsatisfied today

Most published ML accuracy claims today cannot satisfy any of those obligations. Why:

- The metric, threshold, dataset slice, and seed are reported **after** the experiment runs.
- Nothing cryptographic was committed **before**.
- A reviewer or regulator cannot, even in principle, distinguish honest reporting from post-hoc threshold tuning, slice selection, or silent re-runs.

Notified bodies, internal auditors, and post-market monitoring teams therefore inherit a problem with no forensic surface. They cannot point to a record that says *"this is what was committed, and this is what was verified."* They can only point to documents — model cards, datasheets, internal reports — which were authored after the numbers were observed.

The AI Act does not tolerate this gap. It names *automatic*, *traceable*, *retained* logging. Article 12 specifically requires **tamper-evidence over the full system lifetime**.

---

## What PRML provides

**PRML v0.1** is a small specification: a YAML manifest that binds an evaluation claim — *(metric, comparator, threshold, dataset hash, random seed, producer identity)* — to a single SHA-256 digest, computed over a canonical byte sequence, **before the experiment runs**.

A verifier with the manifest, the dataset, and the model can independently:

1. Recompute the digest. Detect tampering.
2. Recompute the dataset hash. Detect substitution.
3. Execute the evaluation under the bound seed. Compute the verdict.
4. Emit one of four exit codes: `PASS` (0), `FAIL` (10), `TAMPERED` (3), `GUARD` (11).

Honest amendments — *"we found twelve mislabeled examples and re-ran"* — do not overwrite. They append, via a forward-only `prior_hash` chain. The chain **is** the audit log.

The verifier requires no trust in the producer, no registrar, no third party, no internet connection. SHA-256 plus the manifest plus the dataset plus the model is sufficient.

---

## Article-by-article mapping

The full mapping document is at [spec/compliance/AI-Act-mapping-v0.1.md](https://github.com/studio-11-co/falsify/blob/main/spec/compliance/AI-Act-mapping-v0.1.md). Summary:

| Article | Obligation | PRML field(s) |
|---|---|---|
| 12 | Automatic logging, traceable over lifetime | `claim_id`, `created_at`, exit code, `prior_hash` chain |
| 17 | Quality management records | manifest body + sidecar hash + chain hash |
| 18 | 10-year retention | append-only chain, plain-text manifest format |
| 50 | Transparency to deployers | published canonical URL, CC BY 4.0 spec, deterministic verifier |
| 72 | Post-market monitoring | amendment chain over deployment lifetime |
| 73 | Serious incident reporting | `notes` field on amendments documenting incident context |

NIST AI RMF and ISO/IEC 42001 mappings are documented in the same file.

---

## Three concrete use cases

### 1. Pre-market: notified body audit

Your notified body asks: *"Show us the evaluation records for the accuracy claim in your Article 11 technical documentation."*

With PRML, the answer is one URL plus one chain hash. The notified body downloads the manifest, recomputes the SHA-256, executes the verifier, and obtains a deterministic verdict. Their internal log records *"verified offline at <timestamp>, hash <h>, verdict PASS."* Nothing in the audit depends on trusting your team's word, your CI logs, or your experiment-tracking provider.

### 2. Quality management: Article 17 + ISO 42001 §9.2

Your internal auditor asks: *"What evaluation procedures were applied, when, and what were the outcomes?"*

The PRML chain answers this directly. Each manifest is a documented procedure. Each amendment is a documented change. The chain order is the timeline. The notes field is the rationale. ISO 42001 §7.5 (control of documented information) is satisfied by content addressing: the document's identity is its hash, and any modification produces a new identity.

### 3. Post-market: Article 72 monitoring

Your post-market monitoring plan requires recurring evaluation against drift. PRML supports this natively: each scheduled re-evaluation is a new manifest, linked to the prior via `prior_hash`. If the drift threshold is breached, the chain records both the breach and the remediation. The same chain is what Article 73 (serious incident reporting) references when an incident traces back to a specific evaluation event.

---

## What PRML is not

- **Not a compliance product.** PRML is a primitive. The reference implementation (`falsify`) is single-file Python under MIT. The specification is under CC BY 4.0. There is no SaaS, no subscription, no enterprise license.
- **Not a substitute for a notified body.** Notified bodies assess your full conformity package. PRML produces one component of the technical-documentation portion of that package.
- **Not a substitute for your QMS.** Your quality management system stays where it is. PRML provides the cryptographic substrate for the documents your QMS already produces.
- **Not a substitute for model cards or datasheets.** Those remain. PRML sits underneath them, providing the verifiable hash that a model card cites when it reports an accuracy number.
- **Not, on its own, sufficient for Annex III high-risk evidence.** The hash proves a claim was *committed*; it does not prove the producer committed *before* running, or published *every* claim. v0.1 requires a deployment-level anchor (§8.1) to close the selective-publication and back-dating gaps before the record is audit-grade.
- **Not a measure of dataset adequacy.** `dataset.hash` proves the evaluation ran on exactly those bytes. It does **not** prove the dataset is representative, balanced, or sufficient — the Article 10 data-governance duties are a separate, substantive obligation outside PRML's scope.

---

## What PRML does for your team, today

A team adopting PRML in v0.1 form gets:

- **A single command to lock a claim:** `falsify lock <claim>`. Output: a sidecar SHA-256.
- **A single command to verify it:** `falsify verify <claim> --observed <value>`. Output: an exit code.
- **A GitHub Action** (`falsify-verify`) that runs the verifier in CI and fails the build on any tampered or falsified manifest.
- **Twelve conformance test vectors** with locked SHA-256 digests, so a second implementation in any language can prove byte-for-byte conformance.
- **An ArXiv preprint** (working draft, 14 pages, CC BY 4.0) that documents the spec, the canonicalization, the threat model, and the regulatory mapping in citable form.

The cost is one hash function call per claim. The output is a record that survives any team turnover, any tool migration, any vendor transition — because the verifier needs only the manifest, the dataset, the model, and SHA-256.

---

## Where to start

| If you are… | Start with |
|---|---|
| A compliance lead evaluating PRML for adoption | The [Article-by-article mapping](https://github.com/studio-11-co/falsify/blob/main/spec/compliance/AI-Act-mapping-v0.1.md) |
| A notified body assessor | The [verifier exit-code semantics](https://spec.falsify.dev/v0.1#verification-protocol) |
| An ML team lead | The [reference implementation](https://github.com/studio-11-co/falsify) and [GitHub Action](https://github.com/studio-11-co/falsify/tree/main/.github/actions/falsify-verify) |
| A specification reviewer | The [v0.1 spec](https://spec.falsify.dev/v0.1) and the [Discussion #6](https://github.com/studio-11-co/falsify/discussions/6) |

For substantive feedback on the regulatory mapping, the threat model, or the specification: `hello@falsify.dev`.

The **v0.2 freeze is targeted 2026-05-22**. Three-week window for substantive review. Comments on the field-to-obligation bindings carry the most weight at this stage.

---

*Working draft v0.1, CC BY 4.0. This document is informational and not legal advice. Conformity assessment under the EU AI Act is the responsibility of the provider and the notified body involved.*
