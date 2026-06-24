# PRML v0.1 — EU AI Act Compliance Mapping

**Working draft for legal & compliance review.**
**Editor:** Cüneyt Öztürk — `hello@falsify.dev`
**Date:** 2026-05-01
**Spec under review:** [PRML v0.1](https://spec.falsify.dev/v0.1)
**Regulation:** Regulation (EU) 2024/1689 of 13 June 2024 ("AI Act")
**License:** CC BY 4.0

---

## 0. Purpose of this document

This document maps fields of the **Pre-Registered ML Manifest (PRML) v0.1** specification to specific articles of Regulation (EU) 2024/1689. It is intended to assist:

1. **Providers** of high-risk AI systems (Annex III) preparing technical documentation under Article 11 and logging infrastructure under Article 12.
2. **Notified Bodies** assessing conformity under Article 43.
3. **National competent authorities** auditing post-market surveillance records under Article 72.
4. **Compliance lawyers** evaluating whether PRML satisfies named record-keeping obligations.

It is **not legal advice**. It is an editorial position by the spec author about which obligations the format mechanically supports and which it does not.

> **Reading note.** Article references are to the consolidated text of Regulation (EU) 2024/1689 published in the Official Journal on 12 July 2024, with general entry into force 1 August 2024 and high-risk obligations originally set for 2 August 2026 under Article 113, deferred to 2 December 2027 by the EU Digital Omnibus (agreed May 2026).

---

## 1. Scope

### 1.1 What PRML can satisfy

PRML provides cryptographic integrity for **a single class of records**: the *pre-experimental commitment* to a quantitative evaluation claim — metric, comparator, threshold, dataset content, seed, producer identity. It does so via SHA-256 over a deterministic canonical byte sequence, computed and committed *before* the evaluation runs.

PRML therefore mechanically supports compliance with obligations that require:

- automated logging of evaluation events with tamper-evidence
- retention of technical documentation in machine-readable form
- auditable post-market monitoring of accuracy claims
- transparency of evaluation methodology to deployers and end users

### 1.2 What PRML does **not** satisfy

PRML does not address:

- **Risk management system** under Article 9 (process obligation, not record format)
- **Data governance and management** under Article 10 (substantive bias and quality obligations)
- **Human oversight** under Article 14 (operational obligation)
- **Accuracy, robustness, cybersecurity** under Article 15 (substantive system properties)
- **Conformity assessment procedures** under Articles 43-49 (process obligation)
- **Fundamental rights impact assessment** under Article 27 (substantive assessment)

PRML is a **primitive for record integrity**. It does not assess *whether* a claim is correct, fair, or sufficient — only *that* the claim was committed before it was tested.

> **Scope limit for high-risk use.** v0.1 makes a committed claim tamper-evident; it does **not**, on its own, defend against *selective publication* (publishing only the claims that passed) or *back-dating* (authoring a manifest after the fact). These are the adversaries most relevant to an Annex III audit. v0.1 deployments used as Article 12 evidence **MUST** adopt one of the three deployment-level mitigations in [spec §8.1](https://spec.falsify.dev/v0.1#threat-model) — publish-before-run anchor, sequential `claim_id` allocation, or external pre-registration anchor. A v0.1 deployment that adopts none of them is **not suitable** for standalone Annex III evidence submission. The "Coverage" labels below describe what the format *mechanically supports*, conditional on this discipline — they are not certifications.

---

## 2. Article-by-article mapping

### 2.1 Article 12 — Record-keeping (logging)

> *"High-risk AI systems shall technically allow for the automatic recording of events ('logs') over the lifetime of the system. […] The logging capabilities shall […] enable the recording of events relevant for: (a) identifying situations that may result in the AI system presenting a risk […] (b) facilitating the post-market monitoring referred to in Article 72; and (c) monitoring the operation of high-risk AI systems referred to in Article 26(5)."*

| Article 12 obligation | PRML mechanism | Field(s) |
|---|---|---|
| Automatic recording of evaluation events | `lock` action emits manifest + sidecar hash, exit code 0/3/10/11 logged | `claim_id`, `created_at`, exit code |
| Identifying risk situations | TAMPERED (exit 3) and FAIL (exit 10) verdicts are deterministic | comparator + threshold + verifier exit code |
| Facilitating post-market monitoring | forward-only `prior_hash` chain spans system lifetime | `prior_hash`, `chain_hash` |
| Lifetime preservation | plain text artifact + sidecar; no proprietary runtime needed to read | YAML 1.2 subset |

**Coverage:** **Full** for the evaluation-claim subset of Article 12 events — and only conditional on the §8.1 anti-gaming discipline noted above; without it, even this subset is not audit-grade. Article 12 also requires logging of input data references, identification of natural persons reviewing outputs, and reference databases — these are *complementary* to PRML, not alternatives.

**Editor note:** PRML does not log inference-time events (per-request prediction logs). Those belong in a separate logging system. PRML covers only the *evaluation claim* layer.

---

### 2.2 Article 17 — Quality management system

> *"Providers of high-risk AI systems shall put a quality management system in place that ensures compliance with this Regulation. […] The quality management system shall include at least the following aspects: […] (g) systems and procedures for data management […] (h) the risk management system referred to in Article 9; (i) the setting-up, implementation and maintenance of a post-market monitoring system, in accordance with Article 72; (j) procedures related to the reporting of a serious incident in accordance with Article 73; (k) the handling of communication with national competent authorities […]"*

| Article 17 obligation | PRML mechanism |
|---|---|
| §17(g) data management procedures | `dataset.id` + `dataset.hash` provide immutable reference to evaluation dataset bytes |
| §17(i) post-market monitoring | amendment chain (`prior_hash`) records evaluation re-runs over time |
| §17(j) serious incident reporting | exit code 10 (FAIL) on a previously-PASSing manifest is a deterministic incident trigger |

**Coverage:** **Partial.** PRML provides the *records* a QMS audits. It does not constitute a QMS. A QMS auditor will use PRML manifests as evidence of §17(g)/(i)/(j) procedures functioning correctly.

---

### 2.3 Article 18 — Documentation keeping

> *"For a period ending 10 years after the high-risk AI system has been placed on the market or put into service, the provider shall keep at the disposal of the national competent authorities: (a) the technical documentation referred to in Article 11; (b) the documentation concerning the quality management system referred to in Article 17; (c) the documentation concerning the changes approved by notified bodies, where applicable; (d) the decisions and other documents issued by the notified bodies, where applicable; (e) the EU declaration of conformity referred to in Article 47."*

| Article 18 obligation | PRML mechanism |
|---|---|
| 10-year retention | manifests are plain text (UTF-8 YAML) + sidecar (hex SHA-256); zero binary dependencies; readable in 2046 by any tool that can read UTF-8 |
| Tamper evidence over the retention period | hash chain detects any retroactive edit; chain hash anchors arbitrarily long history into a single 32-byte value |
| Format stability | spec is versioned; v0.1 manifests remain readable indefinitely; algorithm agility planned in v0.2 for post-quantum migration |

**Coverage:** **Full** for the technical documentation evaluation-claim subset.

**Editor note:** PRML's 10-year retention property is structural, not operational. The provider still must store the manifests somewhere reliable (object storage, git, audit-log appliance). PRML guarantees *integrity* of stored bytes; it does not guarantee *availability*.

---

### 2.4 Article 50 — Transparency obligations for providers and deployers

> *"Providers shall ensure that AI systems intended to interact directly with natural persons are designed and developed in such a way that the natural persons concerned are informed that they are interacting with an AI system […]. Providers […] shall ensure that the outputs of the AI system are marked in a machine-readable format and detectable as artificially generated or manipulated."*

| Article 50 obligation | PRML mechanism |
|---|---|
| Machine-readable transparency to deployers | manifest is YAML; canonical URL `https://spec.falsify.dev/v0.1`; manifests can be served alongside model artifacts |
| Detectability of AI-system claims | claim hash + canonical URL + producer ID provides a verifiable triple a deployer or end user can independently check |

**Coverage:** **Indirect.** Article 50 targets disclosure to natural persons; PRML targets disclosure to *technical reviewers*. PRML supports the deployer-facing layer of transparency obligations under Article 50(2).

---

### 2.5 Article 72 — Post-market monitoring system

> *"Providers shall establish and document a post-market monitoring system in a manner that is proportionate to the nature of the AI technologies and the risks of the high-risk AI system. […] The post-market monitoring system shall actively and systematically collect, document and analyse relevant data which may be provided by deployers or which may be collected through other sources on the performance of high-risk AI systems throughout their lifetime."*

| Article 72 obligation | PRML mechanism |
|---|---|
| Active and systematic collection of performance data | each evaluation run produces a manifest; chain accumulates over time |
| Lifetime tracking | `prior_hash` provides total ordering of evaluation events |
| Documentation of analysis | exit codes (0/10/3/11) provide deterministic, machine-readable verdicts |

**Coverage:** **Full** for accuracy-claim post-market monitoring — conditional on the §8.1 discipline above. PRML is the natural format for the evaluation slice of an Article 72 plan; it does not cover non-evaluation monitoring signals (field incident reports, deployer feedback, drift telemetry), which are complementary.

---

### 2.6 Article 73 — Reporting of serious incidents

> *"Providers of high-risk AI systems placed on the Union market shall report any serious incident […] to the market surveillance authorities of the Member States where that incident occurred."*

| Article 73 obligation | PRML mechanism |
|---|---|
| Detecting a serious incident | a manifest that previously verified PASS but now verifies FAIL (exit code 10) is a deterministic incident signal |
| Documenting the incident | the chain of manifests provides timestamped evidence of when the regression appeared |
| Reporting to authorities | manifest hashes are short, transmissible, and verifiable offline |

**Coverage:** **Partial.** PRML provides the technical detection and evidence layer. The reporting *process* (timing, recipients, format) is a separate operational obligation.

---

## 3. Annex IV — Technical documentation

Article 11 requires the provider to draw up technical documentation according to **Annex IV**. The relevant Annex IV items for PRML are:

| Annex IV item | PRML coverage |
|---|---|
| §1(c) software description | spec URL + reference impl URL + commit hash |
| §2(d) capabilities and limitations | claim metadata: metric, threshold, dataset, seed |
| §2(e) accuracy and performance metrics | `metric` + `threshold` field with hash binding |
| §2(g) test reports | manifest + verifier exit code log |
| §3 detailed information about monitoring | chain hash + amendment log |
| §5 description of the changes made through the system's lifetime | forward-only `prior_hash` chain *is* the change log |

**Coverage:** **Full** for §2(e), §2(g), §3, §5. **Supporting** for §1(c), §2(d).

---

## 4. NIST AI RMF v1.0 cross-mapping

For organizations operating across jurisdictions, PRML also aligns with NIST AI Risk Management Framework v1.0 (January 2023):

| NIST RMF function | Subcategory | PRML field/mechanism |
|---|---|---|
| **GOVERN** 1.1 | accountability mechanisms documented | `producer.id` + optional signature |
| **GOVERN** 4.1 | organizational practices for documenting | manifest format itself |
| **MAP** 5.1 | impact characterization | metric + threshold commitment |
| **MEASURE** 2.3 | systems are evaluated for valid and reliable performance | hash binding before evaluation |
| **MEASURE** 2.7 | AI system security and resilience | TAMPERED exit code |
| **MEASURE** 4.2 | regular assessments | amendment chain over time |
| **MANAGE** 4.3 | mechanisms for continual improvement | `prior_hash` chain |

---

## 5. ISO/IEC 42001:2023 cross-mapping

| ISO/IEC 42001:2023 clause | PRML mechanism |
|---|---|
| 7.5.1 documented information — general | manifest YAML + sidecar hash |
| 7.5.2 creating and updating | canonical serialization rules; amendment via new manifest, never overwrite |
| 7.5.3 control of documented information | hash binding + chain prevents undetected modification |
| 8.4 operational planning and control of AI | pre-experimental commitment is an operational control |
| 9.2 internal audit | auditor recomputes hashes offline; no trust in provider tooling required |
| 10.1 nonconformity and corrective action | TAMPERED (3) and FAIL (10) verdicts trigger corrective action |

---

## 6. Worked example — high-risk system under Annex III

**Scenario.** A provider deploys an AI system for **CV screening** under Annex III §4(a) (employment). Article 12 requires automated logging; Article 18 requires 10-year retention; Article 72 requires post-market monitoring.

**Provider workflow with PRML:**

1. Before each model release, the provider runs `falsify lock` on the evaluation harness, producing `release-2026-Q3.prml.yaml` + `release-2026-Q3.prml.sha256`.
2. Manifest binds: `metric: f1`, `threshold: 0.78`, `dataset.hash: <sha256 of validation set bytes>`, `seed: 42`, `producer.id: company.example`.
3. The hash + manifest are committed to the company's release artifact registry and to the regulator-facing audit appliance.
4. Six months later, a deployer reports an accuracy regression. The provider runs `falsify verify release-2026-Q3.prml.yaml`. If exit code 10 (FAIL) appears on a manifest that previously emitted exit code 0, this is a deterministic Article 73 incident trigger.
5. The provider issues an amended manifest `release-2026-Q3-amend-1.prml.yaml` with `prior_hash: <hash of original>`. The chain is the audit log.

**Notified Body audit at year 3:**

1. The auditor receives the chain hash (32 bytes).
2. The auditor recomputes the canonical bytes of every manifest in the chain offline.
3. The auditor recomputes the chain hash. Match → integrity verified, no provider trust required.

This workflow satisfies the **records** half of Articles 12, 17(i), 18, 72, and 73 with arithmetic, not process attestation.

---

## 7. What PRML still requires from the provider

PRML is a primitive. To use it in an AI Act compliance posture, the provider still must:

1. **Establish a logging infrastructure** that captures manifests and sidecars at lock/verify time and stores them durably (object storage, immutable bucket, audit appliance).
2. **Define a retention policy** consistent with Article 18 (10 years).
3. **Train evaluation engineers** to lock manifests *before* running experiments, not after. This is the single most common adoption failure.
4. **Embed verifier output in CI** so a TAMPERED or FAIL exit code halts deployment automatically.
5. **Document the QMS** per Article 17 — including PRML usage — separately from PRML itself.
6. **Sign manifests** for high-risk Annex III systems — `producer.signature` is optional in v0.1 and **strongly recommended** for high-risk usage. Mandatory in v0.2.

PRML does not replace these obligations. It makes them auditable.

---

## 8. Open questions for legal review

1. Is `producer.id` (DNS-style identifier) sufficient as the §17(j)/Article 73 incident-reporting attribution, or is a legal entity identifier (LEI / ISO 17442) required?
2. Does the EU Cybersecurity Act (Reg. 2019/881) impose additional obligations on the SHA-256 dependency? (Editor view: no — SHA-256 is FIPS 180-4 standard and ENISA-recommended.)
3. Article 12(2) requires logging be "appropriate to the intended purpose." Are evaluation-claim manifests (PRML) sufficient for systems whose intended purpose is *not* directly tied to a specific accuracy threshold (e.g., generative systems)?
4. For SMEs invoking Article 62 derogations, can PRML manifests substitute for parts of the Annex IV documentation, given their compactness?
5. Algorithm agility: when SHA-256 is deprecated (post-quantum era, est. 2030+), how does a 10-year retention obligation interact with hash migration?

These questions are open. The spec author invites compliance lawyers to weigh in on the GitHub Discussion thread or via `hello@falsify.dev`.

---

## 9. Disclaimer

This document is editorial commentary by the spec author. It is **not legal advice**, has **not been reviewed by a notified body**, and **does not bind any regulator**. Providers are responsible for their own conformity assessments under Article 43.

The author's position is that PRML provides a defensible technical foundation for *named record-keeping obligations* under the AI Act. Whether a particular provider's overall posture is conformant depends on factors well outside any specification.

---

## 10. References

- Regulation (EU) 2024/1689 of 13 June 2024 (AI Act). OJ L 2024/1689.
- Annex III: List of high-risk AI systems referred to in Article 6(2).
- Annex IV: Technical documentation referred to in Article 11(1).
- NIST AI RMF v1.0, January 2023, NIST AI 100-1.
- ISO/IEC 42001:2023, Information technology — Artificial intelligence — Management system.
- NIST FIPS 180-4 (2015), Secure Hash Standard (SHS).
- ENISA Guidelines on Cryptographic Algorithms (2024).
- PRML v0.1 specification: https://spec.falsify.dev/v0.1
- PRML reference implementation: https://github.com/studio-11-co/falsify

---

*Document v0.1, drafted 2026-05-01 by Cüneyt Öztürk. Public review via GitHub Discussions on `studio-11-co/falsify` or `hello@falsify.dev`. CC BY 4.0.*
