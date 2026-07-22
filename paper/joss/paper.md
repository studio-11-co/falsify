---
title: 'falsify: Pre-Registered ML Manifests for verifiable evaluation claims'
tags:
  - Python
  - machine learning
  - evaluation
  - pre-registration
  - reproducibility
  - cryptographic provenance
  - audit
  - AI safety
authors:
  - name: Cüneyt Öztürk
    orcid: 0009-0003-8536-3491
    corresponding: true
    affiliation: 1
affiliations:
  - name: Independent researcher
    index: 1
date: 21 July 2026
bibliography: paper.bib
---

# Summary

`falsify` is the Python reference implementation of **PRML** (Pre-Registered ML
Manifest), an open specification for committing a machine learning evaluation
claim to a SHA-256 hash *before* the experiment runs. A claim is a small
UTF-8 YAML manifest with nine required fields — schema version, metric,
comparator, threshold, dataset content hash, seed, producer identity, claim
identifier and timestamp — and the hash is computed over canonical bytes per
deterministic rules in §3 of the v0.1 specification [@prml_spec_v0_1]. Any
retroactive edit of the manifest breaks the hash, so post-hoc tampering with
a threshold or dataset is detectable by any third party with the manifest
text and a SHA-256 implementation, without producer trust or vendor runtime.

The PRML reference implementation is a single-file Python 3.10+ CLI
(`falsify_prml.py`, ~500 lines) with one runtime dependency (PyYAML); the
same package ships `falsify-engine`, a workflow CLI that locks, runs and
guards claims end to end.
Three companion implementations in JavaScript [@falsify_js], Go and Rust
reproduce byte-equivalent output across a suite of 21 conformance vectors
(13 v0.1 normative plus 8 v0.2 candidate) and reject a shared suite of 14
negative vectors (control characters and non-portable scalars), so a reader of any claim can
re-derive the SHA-256 offline using the language of their choice. A
content-addressed public registry, three regulatory crosswalks (EU AI Act
technical documentation under Art. 11 / Annex IV, NIST AI Risk Management
Framework 1.0, ISO/IEC 42001:2023), a
GitHub Action for continuous-integration enforcement, and adapters for
MLflow and Inspect AI complete the ecosystem; the Inspect adapter is
listed on the UK AI Safety Institute's Inspect extensions page.

# Statement of need

A published machine learning evaluation claim ("our model achieves 0.94
accuracy on benchmark X") is, in current practice, an unverifiable
assertion. A reader has no mechanism to confirm whether 0.94 was the
threshold the authors had committed to *before* observing the result, or a
value chosen after the fact to clear the bar of acceptability. This is not
a hypothetical concern: meta-research on the published ML literature
[@gundersen_2018; @pineau_2021] has documented widespread inability to
reproduce claimed results, and benchmark over-fitting and selective
reporting are widely recognised failure modes [@hooker_2020;
@bowman_2022; @raji_2021].

Pre-registration is the standard methodological response in scientific
disciplines facing the same problem. Clinical trial registries [@dickersin_2003],
the Open Science Framework [@nosek_2018] and the AsPredicted platform have
made commitment-before-observation a normal practice in psychology,
biomedicine and the social sciences. Machine learning has had effectively
no equivalent infrastructure. Existing reproducibility tools focus on
*re-running* an experiment (containers, environment specification, data
versioning) or on *documenting* a model after it ships (Model Cards
[@mitchell_2019], Datasheets for Datasets [@gebru_2021]). Neither of these
addresses the threshold-commitment problem directly.

`falsify` and the PRML format aim at that specific gap. A locked manifest
is a small, tamper-evident artefact that an auditor, reviewer or regulator
can verify offline. The format is intentionally minimal — nine fields,
8 KB at most, plain UTF-8 — so it can be archived for the decade-scale
retention horizons that emerging AI regulation requires (notably Article
18 of Regulation (EU) 2024/1689). The format is also intentionally not
a complete publication-integrity system: §8.1 of the specification names
selective non-publication as out of scope, and the cookbook documents
how to pair PRML with Sigstore for execution integrity.

`falsify` has been used in three independent contexts: as the
reference verifier for the 21 published conformance vectors, as the
content-addressing layer behind a public registry whose receipts are
Ed25519-signed, countersigned by an RFC 3161 timestamp authority and
mirrored to the Rekor transparency log, and as the underlying primitive cited
in subcategory-level crosswalks to the EU AI Act, the NIST AI RMF and
ISO/IEC 42001 that practitioners can hand to compliance reviewers as
documented evidence.

# Software description

The repository hosts:

- **Specification text** (`spec/PRML-v0.1.md`): RFC-style, CC BY 4.0 licensed,
  ~18 pages covering the canonicalization rules, manifest field semantics,
  exit-code contract (0/PASS, 10/FAIL, 3/TAMPER, 11/GUARD), amendment chain
  via `prior_hash`, and integration guidance.
- **Reference implementation** (`falsify_prml.py`): the PRML CLI, ~500 LOC
  including the canonicalizer, validator, verifier (with dataset content
  check) and in-toto attestation output; `falsify.py` adds the workflow
  engine (lock/run/verdict/guard) that binds verdicts to the locked bar.
- **Test vectors** (`spec/test-vectors/v0.1/`): 13 conformance vectors with
  locked SHA-256 digests; the multi-language CI runs these against four
  reference implementations on every push.
- **Companion projects** as separate repositories: `falsify-js` (JavaScript
  reference implementation), `falsify-inspect` (Inspect AI adapter),
  `mlflow-falsify` (MLflow run-context plugin), `prml-verify-action` (GitHub
  Marketplace composite action for CI gating), `falsify-cookbook` (11
  patterns plus 4 anti-patterns), and `falsify-integrity-index` (public
  scorecard of how 27 well-known ML eval claims meet the nine PRML
  falsifiability criteria).

The PRML JSON Schema is in the SchemaStore catalog [@schemastore], so
`*.prml.yaml` files autocomplete in any editor with SchemaStore support
(VS Code, JetBrains, Helix, Zed, Cursor). Spec, conformance vectors and
all four reference implementations are content-addressed in Zenodo
[@prml_zenodo] and archived in Software Heritage.

# Acknowledgements

PRML draws methodologically on the pre-registration literature in
psychology, clinical trials and the broader meta-science movement. The
specification was reviewed during a public v0.2 RFC period closing on
22 May 2026; the author thanks the participants of that review and the
maintainers of the awesome-lists that included PRML in their curated
resources during early development.

# References
