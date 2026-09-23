# PRML v0.1 — EU AI Act Compliance Mapping, v0.2

**Working draft for legal and compliance review. Supersedes v0.1 (1 May 2026).**
**Editor:** Cüneyt Öztürk, Falsify OÜ (Tallinn, registry code 17574308) — `hello@falsify.dev`
**Date:** 2026-09-09
**Spec under review:** [PRML v0.1](https://spec.falsify.dev/v0.1) (Community Specification License 1.0; reference implementations MIT)
**Regulation:** Regulation (EU) 2024/1689 of 13 June 2024 ("AI Act"), as amended by Regulation (EU) 2026/1744 (Digital Omnibus on AI, in force 27 July 2026)
**License of this document:** CC BY 4.0

---

## What changed since v0.1

1. **Dates.** High-risk obligations for Annex III systems apply from **2 December 2027**; for Annex I embedded systems from **2 August 2028** (Regulation (EU) 2026/1744, amending Article 113). Article 50 transparency duties applied on 2 August 2026, unchanged; systems on the market before that date have until 2 December 2026 for the Article 50(2) marking duty (new Article 111(4)).
2. **Starting point moved to Article 9(8).** v0.1 treated Article 9 as out of scope ("process obligation"). That was too broad. Article 9(8) contains the one sentence in the operative text that names a *pre-specification* obligation for evaluation criteria, and it is the natural entry point for this format. Article 9 as a risk-management *process* remains out of scope.
3. **New sections** for Article 9(8), Article 13(3)(b)(ii), Article 15(3), the Article 25(2) hand-over duty and Article 75a(6)(b) retention order (both introduced by the Omnibus).
4. **A "where the Act says *prior*" table** (§1) replaces the scattered treatment.
5. **Evidence semantics corrected.** v0.1 said a manifest hash is "computed and committed *before* the evaluation runs". The format cannot establish that on its own. What a PRML record with an independent anchor establishes is: *this criteria object existed no later than time T and has not changed since.* Whether the evaluation ran after T is a separate property ("execution linkage") that v0.1 does not carry; see §4. Every coverage statement below is rewritten under that rule.
6. **Article 17 sub-points corrected.** v0.1 cited (g), (i), (j) for data management, post-market monitoring and incident reporting. The correct letters in the OJ text are (f), (h) and (i); record-keeping is (k).
7. **The registry.** Since 3 September 2026 the public registry at registry.falsify.dev issues Ed25519-signed receipts with an RFC 3161 timestamp from a public time-stamping authority and an entry in a public transparency log (Rekor), and accepts *sealed* commitments (digest and time public, criteria withheld until reveal). This is the "external pre-registration anchor" that v0.1 §8.1 described as one of three mitigations; it is now a concrete option rather than a recommendation.

**Positioning rule applied throughout.** The obligation in the Act is that metrics and thresholds be *prior defined* and *appropriate*. The Act does not require timestamps, hashes, or any third party. A PRML record is *stronger evidence of a fact the Act already asks for*; it is not an additional obligation and this document never says otherwise.

---

## 0. Purpose and audience

This document maps the fields of the **Pre-Registered ML Manifest (PRML) v0.1** to specific provisions of the AI Act. It is written for providers of high-risk AI systems preparing technical documentation (Article 11, Annex IV), notified bodies assessing conformity (Article 43), market surveillance authorities, and compliance counsel. It is **not legal advice**; it is the spec author's editorial position on which obligations the format mechanically supports, which it supports only partly, and which it does not touch.

> **Reading note.** Article references are to Regulation (EU) 2024/1689 as amended by Regulation (EU) 2026/1744. Quotations were checked on 9 September 2026 against the consolidated text as published by the EU AI Act Service Desk mirror; the tail of Article 9(8) differs slightly between the 2024 OJ wording and the consolidated display, so only the common part is quoted. Verify against EUR-Lex (CELEX 32024R1689, 32026R1744) before citing in a filing.

---

## 1. Where the Act says "prior": the pre-specification table

| Provision | What it asks for (summary; quotation in the section named) | Evidence object | What a PRML record establishes | What it does not |
|---|---|---|---|---|
| **Art. 9(8)** | testing "against prior defined metrics and probabilistic thresholds that are appropriate to the intended purpose" | metric, comparator, threshold, test data identity, system version | the criteria object existed no later than the anchor time and is unchanged | that the criteria were *appropriate*; that the test ran *after* the anchor (§4) |
| Art. 9(6) | testing to identify risk-management measures; consistent performance for the intended purpose | test dates bound to a system version | `producer.id` and `created_at` name the system and the record time | consistency of performance; ordering of test vs. record |
| Art. 10 | data governance: examination of training, validation and testing data | dataset identity and content hash | `dataset.id` + `dataset.hash` fix *which* test data the criteria refer to | the quality, representativeness or lawfulness of the data |
| **Art. 11 / Annex IV 2(g)** | validation and testing procedures, test data and characteristics, metrics used, dated and signed test logs and reports | the 2(g) section of the technical file | a digest and anchor time that the 2(g) section can cite next to the report date | the report itself, its signature, or its date |
| Annex IV 4 | appropriateness of the performance metrics | rationale | nothing; a record names the metric, it does not justify it | appropriateness (provider's and assessor's judgement) |
| Annex IV 6 / Art. 17(1)(a) | management of modifications; changes over the lifetime | change log of criteria | each criteria version has its own digest; a later record can reference an earlier one (`prior_hash` where used) | why a threshold changed, or who approved it |
| **Art. 13(3)(b)(ii)** | instructions for use state "the level of accuracy, including its metrics […] against which the high-risk AI system has been tested" | declared level ↔ tested criteria | the declared metric and level can be compared to the recorded threshold; a mismatch is visible | the declaration itself; whether the declared level is adequate |
| **Art. 15(3)** | accuracy levels and metrics "declared in the accompanying instructions of use" | same as above | same as above | accuracy, robustness or cybersecurity of the system |
| Art. 17(1)(d) | examination, test and validation procedures "before, during and after the development" and their frequency | procedure + records | manifests are one record type such a procedure can produce | the procedure, the QMS, its audit |
| Art. 17(1)(k) | record-keeping of all relevant documentation | records | plain-text, content-addressed records with an offline verifier | storage, availability, retention policy |
| Art. 18 | documentation kept for ten years | durable, tamper-evident records | integrity over the period (digest recomputable in 2036 with any SHA-256 tool) | availability (where the bytes are kept) |
| **Art. 72(2)–(3)** | post-market monitoring plan; systematic collection and analysis of performance data; plan is part of Annex IV | monitoring trigger thresholds fixed in the plan | a sealed commitment can fix a monitoring or retraining trigger before field data arrives; the digest goes in the plan | the monitoring system; drift telemetry; deployer feedback |
| Art. 73 | serious incident reporting | the criteria version in force at the incident | a record identifies which criteria the system was released against | detection, timing or content of the report |
| Art. 25(2) (Omnibus) | hand-over of technical documentation, known limitations and failure modes, and test access when another provider takes over a system | records that survive a change of provider | a digest-addressed record does not depend on the original provider's systems to be verified | the hand-over itself |
| Art. 75a(6)(b) (Omnibus) | AI Office may order retention of data and documents needed to assess compliance | records whose time of creation is not in dispute | anchor time from a party the provider does not control | the order, or the provider's compliance with it |

Rows in bold are the provisions this document treats as primary. Rows not in bold are supported only at the record level.

---

## 2. Article-by-article

### 2.1 Article 9(8) — testing against prior defined metrics and thresholds

> *"The testing of high-risk AI systems shall be performed, as appropriate, at any time throughout the development process, and, in any event, prior to their being placed on the market or put into service. Testing shall be carried out against prior defined metrics and probabilistic thresholds that are appropriate to the intended purpose […]"* — Article 9(8)

The obligation has three parts: the metrics and thresholds must exist **before** testing; they must be **appropriate** to the intended purpose; and testing must actually be carried out **against** them. The Act does not say how the first part is to be shown. In practice the technical documentation says "the thresholds were approved on date D, before the test campaign", and the documentation's dates are the provider's own.

| Element of 9(8) | PRML field(s) | Coverage |
|---|---|---|
| metrics | `metric` | record |
| probabilistic thresholds | `threshold`, `comparator` | record |
| against which test data | `dataset.id`, `dataset.hash` | record |
| for which system | `producer.id` (and system version where encoded in it) | record |
| *prior* defined | SHA-256 of the canonical bytes + independent anchor (RFC 3161 token, transparency-log entry) | **existence no later than T**; see §4 for what is not established |
| *appropriate* to the intended purpose | none | **not addressed** |
| testing *carried out against* them | none in v0.1 | **not addressed** (execution linkage, §4) |

**Coverage:** *record-level* for the content of the criteria; *independent time evidence* for the existence of the criteria object; **none** for appropriateness or execution ordering.

**Suggested wording for the technical file.** "The acceptance criteria for this test (metric, comparison rule, threshold, test data identifier and hash) were recorded as a PRML criteria record with SHA-256 *digest*. The digest was independently time-evidenced no later than *T* (RFC 3161 token and transparency-log entry at *permalink*). The test report *TR-n*, dated *D* and signed by *role*, names this digest." The reader can then compare *T* and *D* themselves. Do not write "the criteria were fixed before testing" on the strength of the record alone.

A free two-step flow for this article (check an existing test plan; create a criteria record) is at falsify.dev/ai-act/article-9-8/.

### 2.2 Article 11 and Annex IV 2(g) — technical documentation

> *"the validation and testing procedures used, including information about the validation and testing data used and their main characteristics; metrics used to measure accuracy, robustness and compliance with other relevant requirements set out in Chapter III, Section 2, as well as potentially discriminatory impacts; test logs and all test reports dated and signed by the responsible persons, including with regard to pre-determined changes as referred to under point (f)"* — Annex IV 2(g)

| Annex IV item | PRML coverage |
|---|---|
| 2(b) design specifications, key design choices | none (rationale is prose) |
| 2(d) data requirements, datasheets, training data | `dataset.id`/`dataset.hash` identify the *test* data only; training data are out of scope |
| **2(g)** validation and testing procedures, test data, metrics, dated and signed reports | the criteria part of the section can cite a digest and an anchor time; the report, its date and its signature remain the provider's documents |
| 3 monitoring, functioning and control; capabilities and limitations | a declared limitation can reference the threshold it was tested against |
| 4 appropriateness of the performance metrics | none |
| 5 (as numbered in the consolidated text) risk management system per Article 9 | the 9(8) record set is one input |
| lifetime changes (Article 17(1)(a) modifications; Annex IV "pre-determined changes") | one digest per criteria version; later records may reference earlier ones |

**Coverage:** *supporting* for 2(g) and 3; **none** for 2(b), 2(d) training data, and 4. v0.1 called 2(g) "Full"; that overstated it. A manifest is not a test report.

### 2.3 Articles 13(3)(b)(ii) and 15(3) — declared accuracy levels

> *"the level of accuracy, including its metrics, robustness and cybersecurity referred to in Article 15 against which the high-risk AI system has been tested"* — Article 13(3)(b)(ii)
> *"The levels of accuracy and the relevant accuracy metrics of high-risk AI systems shall be declared in the accompanying instructions of use."* — Article 15(3)

These two provisions create a consistency requirement that is easy to state and rarely evidenced: the level declared to deployers should be the level the system was tested against. A criteria record gives the declared level something to be compared with. If the instructions say "AUC ≥ 0.84 on the hold-out set" and the recorded threshold is 0.84 with the same metric and dataset hash, the two agree; if the instructions say 0.90, the discrepancy is visible to any reader who has both documents.

**Coverage:** *consistency check only.* PRML does not address the substantive Article 15(1) properties (accuracy, robustness, cybersecurity) and does not generate the instructions for use.

### 2.4 Article 12 — record-keeping (logging)

> *"High-risk AI systems shall technically allow for the automatic recording of events (logs) over the lifetime of the system."* — Article 12(1)

Article 12 concerns automatic runtime logging of the system's operation. A PRML manifest is a record *about an evaluation*, not a log of *operation*. The mapping is therefore partial and narrower than v0.1 stated.

| Article 12 element | PRML mechanism | Coverage |
|---|---|---|
| automatic recording | a manifest can be emitted by the evaluation pipeline without human authoring | record type only |
| tamper evidence of a record | SHA-256 over canonical bytes; any edit changes the digest; an anchored digest cannot be silently replaced | the evaluation-criteria record only |
| identification of risk situations (12(2)(a)) | a verifier verdict (pass / fail / tampered) is deterministic once the observed value is supplied | the observed value is producer-asserted; PRML does not measure it |
| post-market monitoring (12(2)(b)) | see §2.6 | partial |
| monitoring of operation (12(2)(c)) | none | **not addressed** |

The Act does not mandate a cryptographic mechanism for logs. Where a provider chooses hash chains, signed entries or external timestamps for its operational logs, that is a design decision under Article 17, and PRML is not that logging system. A separate checklist for Article 12 is at falsify.dev/article-12-checklist/.

### 2.5 Article 17 — quality management system

> *"(d) examination, test and validation procedures to be carried out before, during and after the development of the high-risk AI system, and the frequency with which they have to be carried out; […] (f) systems and procedures for data management […]; (g) the risk management system referred to in Article 9; (h) the setting-up, implementation and maintenance of a post-market monitoring system, in accordance with Article 72; (i) procedures related to the reporting of a serious incident in accordance with Article 73; […] (k) systems and procedures for record-keeping of all relevant documentation and information"* — Article 17(1)

| Article 17(1) point | PRML relation |
|---|---|
| (a) management of modifications | each criteria version has its own digest; the sequence of digests is a change record for the criteria, not for the system |
| (d) test and validation procedures | a procedure that emits a criteria record before each test campaign is one way to satisfy the "before" in (d); the format does not define the procedure |
| (f) data management | `dataset.hash` fixes the test set the criteria refer to |
| (g) risk management system | see §2.1 |
| (h) post-market monitoring | see §2.6 |
| (i) serious incidents | a record identifies which criteria version a release was tested against |
| (k) record-keeping | plain-text records, offline verifier, no proprietary reader |

**Coverage:** *records only.* PRML is not a QMS and does not evidence that one exists or functions.

### 2.6 Article 72 — post-market monitoring

> *"The post-market monitoring system shall be based on a post-market monitoring plan. The post-market monitoring plan shall be part of the technical documentation referred to in Annex IV."* — Article 72(3)

A monitoring plan usually names triggers: a performance floor below which retraining or withdrawal is considered. Those triggers are criteria, and they are subject to the same question as Article 9(8) thresholds: were they set before the field data came in, or adjusted to it? A *sealed* commitment (digest and time public, criteria withheld) lets a provider fix a trigger in advance without disclosing it to deployers or competitors, and reveal it when the plan is audited.

**Coverage:** *the trigger record only.* PRML does not collect performance data, detect drift, or analyse anything.

### 2.7 Article 18 — documentation keeping

> *"For a period ending 10 years after the high-risk AI system has been placed on the market or put into service, the provider shall keep at the disposal of the national competent authorities […] the technical documentation referred to in Article 11"* — Article 18(1)

Manifests are UTF-8 text with a hex sidecar; the digest is SHA-256, a FIPS 180-4 standard. Nothing in the record depends on a vendor, a runtime or this company. **Coverage:** *integrity* over the period. **Not covered:** availability. The provider must still store the records somewhere durable; a public registry entry is one copy, not a retention service. (Algorithm agility for a post-quantum migration is on the v0.2 spec roadmap; it does not affect the readability of v0.1 records.)

### 2.8 Article 73 — serious incidents

A record answers one question in an incident investigation: *which criteria was this release tested against, and when did that criteria object exist?* It does not detect incidents, does not time them, and does not produce the report.

### 2.9 Articles 25(2) and 75a(6)(b) — Omnibus additions

Under amended **Article 25(2)**, an initial provider whose high-risk system is taken over by another provider must hand over technical documentation, documented known limitations and failure modes, and targeted technical access for testing and validation; non-compliance is fineable under Article 99(4). Under new **Article 75a(6)(b)**, the AI Office may order operators to retain all data and documents needed to assess compliance.

Both events are easier with records whose time of creation does not depend on the original provider's word or systems. A digest-addressed record with an independent anchor can be verified by the successor provider or by the AI Office without access to the original provider's tooling. **Coverage:** *record portability and time evidence only.*

### 2.10 Article 50 — transparency (removed from the mapping)

v0.1 mapped Article 50 as "indirect". Article 50 concerns disclosure to natural persons and marking of generated content; a criteria record does neither. The mapping is withdrawn. Article 50 duties have applied since 2 August 2026 and are outside this document.

---

## 3. Cross-mappings (unchanged in substance from v0.1)

**NIST AI RMF 1.0:** MEASURE 2.3 (systems evaluated for valid and reliable performance) and MEASURE 4.2 (regular assessments) are the two subcategories where a criteria record adds evidence; GOVERN 1.1 and 4.1 are supported at the documentation level. **NIST AI 300-1 (Model Profile, initial public draft):** field 6.5 asks for evaluation criteria; our input to the RFC is at falsify.dev/submissions/nist-ai-300-1-ipd/.

**ISO/IEC 42001:2023:** 7.5.3 (control of documented information) and 9.2 (internal audit; the auditor recomputes the digest offline) are the clauses where the format is directly useful; 8.4 (operational planning and control) at the procedure level.

**Harmonised standards.** CEN-CENELEC JTC 21 is drafting the standards intended to support the high-risk requirements (among them EN 18286 for quality management and the prEN 18229 series on logging, accuracy and transparency). None had been cited in the Official Journal at the date of this document; no clause-level mapping is offered until the texts are public and cited. Falsify OÜ's comment paper to JTC 21 is at spec.falsify.dev.

---

## 4. Evidence semantics: what a record proves

This section replaces v0.1 §1.1's "computed and committed before the evaluation runs".

A PRML record with an independent anchor establishes three things:

1. **Content.** A specific criteria object (metric, comparator, threshold, dataset identity and hash, seed, producer) is fixed to the byte; the digest is recomputable by anyone with the bytes and any SHA-256 implementation.
2. **Existence no later than T.** The RFC 3161 token and the transparency-log entry show the digest existed at T, on the clock of parties the provider does not control.
3. **Integrity since T.** Any later change to the criteria produces a different digest.

It does **not** establish:

- that the criteria were **appropriate** (Article 9(8), Annex IV 4);
- that the **test ran after T** ("execution linkage"). This is the property a reviewer needs to conclude "prior defined" from the record alone. In v0.1 the execution side comes from the test logs and the dated, signed test report that Annex IV 2(g) separately requires: if the report is dated after T and names the digest, the two records together document the ordering, but that ordering remains the provider's own account; the record does not establish it independently. A machine-checkable linkage (`prml-linkage/0`) is a v0.3 work item;
- that the **result is correct**, or that the observed value reported against the threshold was measured honestly. The observed value is producer-asserted;
- that the provider did not pre-register several criteria sets and publish only the one that passed (selective publication). v0.1 records one claim; suite-level commitments are a roadmap item.

Any statement in a technical file that relies on a PRML record should be phrased as *existence no later than T* plus a separate dated report, never as "fixed before testing" on the record alone.

---

## 5. Worked example — Annex III credit scoring

**Scenario.** A provider places a creditworthiness scoring component (Annex III, point 5(b)) on the market. Under Article 9(8) it defines, before the pre-market test campaign: AUC ≥ 0.84 on hold-out set HOLDOUT-2026Q2 (SHA-256 of the archive recorded), and a maximum equal-opportunity difference of 0.05 across the protected groups listed in its Annex B.

1. On 11 June 2026 the validation team produces two PRML records (one per metric) and anchors both digests at the public registry; the second is sealed because the fairness threshold is commercially sensitive. Both permalinks carry an RFC 3161 token and a transparency-log entry.
2. The test campaign runs from 24 June. The test report TR-2026-07, signed by the Head of Validation on 2 July 2026, names both digests and reports AUC 0.861 and a difference of 0.038.
3. Annex IV 2(g) of the technical file states: criteria recorded as digests *a* and *b*; independently time-evidenced no later than 11 June 2026; test report dated 2 July 2026 names both digests. The instructions for use (Article 13(3)(b)(ii)) declare "AUC ≥ 0.84 on the hold-out set", matching record *a*.
4. At a conformity assessment three years later, the assessor recomputes both digests from the criteria files, checks the two anchors, reads the report date, and concludes that the criteria object pre-dates the report. The assessor still judges *appropriateness* on the merits.
5. The post-market monitoring plan (Article 72(3)) fixes a retraining trigger as a third, sealed record; it is revealed when the plan is reviewed.

What the records did **not** do: decide that 0.84 was the right threshold, prove that the test used exactly the hold-out set (that rests on the report and the dataset hash), or prove that the reported values are correct.

---

## 6. What the provider still has to do

1. Define criteria that are appropriate to the intended purpose. The record does not help with this.
2. Create the record **before** the test campaign, not after, and anchor it. A record created after the fact is worthless as timing evidence, and an anchored record makes that visible.
3. Keep the dated, signed test report and cite the digest in it. Without the report there is no ordering.
4. Store the records durably for the Article 18 period. The registry is a public copy, not a retention service.
5. Keep the declared accuracy level (Articles 13 and 15) consistent with the recorded threshold.
6. Document the procedure in the QMS (Article 17(1)(d)); the format is not the procedure.

---

## 7. Open questions for legal review

1. Is a producer identifier (`producer.id`, DNS-style) sufficient attribution for Article 73 reporting, or is a legal-entity identifier expected?
2. Where the Omnibus simplified Annex IV for SMEs and small mid-caps, does a compact criteria record satisfy the 2(g) metrics element on its own, given that the report remains required?
3. For Article 72 plans: is a sealed trigger (digest and time public, threshold withheld) acceptable to a notified body as evidence that the trigger was fixed in advance, given that the reveal happens at audit?
4. Does a third-party time anchor from a non-EU time-stamping authority raise any admissibility question before a Member State authority? (Editor's view: the Act requires no timestamp at all, so the anchor is evidence to be weighed, not a formal instrument.)
5. When SHA-256 is eventually deprecated, how does a ten-year retention obligation interact with re-anchoring under a successor algorithm?

Comments to `hello@falsify.dev` or the GitHub issue tracker.

---

## 8. Disclaimer

Editorial commentary by the spec author. Not legal advice; not reviewed by a notified body; binding on no regulator. Providers are responsible for their own conformity assessments under Article 43. Nothing here states or implies that any regulator, standards body or registry operator endorses PRML or Falsify OÜ.

---

## 9. References

- Regulation (EU) 2024/1689 (AI Act), OJ L, 12 July 2024. CELEX 32024R1689.
- Regulation (EU) 2026/1744 (Digital Omnibus on AI), OJ 24 July 2026, in force 27 July 2026. CELEX 32026R1744.
- Annex III (high-risk AI systems referred to in Article 6(2)); Annex IV (technical documentation referred to in Article 11(1)).
- Directive (EU) 2024/2853 (product liability), transposition by 9 December 2026.
- NIST AI RMF 1.0 (NIST AI 100-1, January 2023); NIST AI 300-1 initial public draft (2026).
- ISO/IEC 42001:2023.
- NIST FIPS 180-4, Secure Hash Standard; IETF RFC 3161, Time-Stamp Protocol.
- PRML v0.1 specification: https://spec.falsify.dev/v0.1 (media type `application/vnd.prml+yaml`, IANA registered 3 September 2026).
- Public registry: https://registry.falsify.dev
- Article 9(8) flow: https://falsify.dev/ai-act/article-9-8/

*Document v0.2, 9 September 2026, Falsify OÜ. Supersedes v0.1 of 1 May 2026, which remains available for reference. CC BY 4.0.*
