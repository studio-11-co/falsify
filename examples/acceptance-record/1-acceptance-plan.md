# Acceptance plan

**Plan ID:** AP-2026-001 · **Plan version:** v1 · **Date drafted:** 2026-09-23

> ILLUSTRATIVE. Falsify OÜ plays both the supplier and the client role, on public data, to show a completed record. This is not a client engagement. Signatures are made with demo keys, not by real persons (see README).

## Scope

| | |
|---|---|
| Delivery | Illustrative delivery ACC-DEMO-01 |
| AI system | Credit-scoring classifier that recommends approve / decline for consumer credit applications (illustrative) |
| System version under test | sklearn-logistic-regression-l2-C1.0, trained by `run_acceptance.py` at seed 42 |
| Supplier | Falsify OÜ, acting as illustrative supplier |
| Client | Illustrative client (role played by Falsify OÜ) |
| Acceptance period covered | One acceptance round, planned test window 2026-09-23 |

This plan covers one system version and one acceptance round. It does not cover other versions, other test rounds, or the system's operation after go-live. A plan that has not changed since it was sealed does not show that no other plan or test existed.

## Acceptance criteria

| ID | Metric | Pass if | Test data (identifier and SHA-256) | Configuration | Criteria record (PRML manifest SHA-256) |
|---|---|---|---|---|---|
| C1 | Impact ratio for sex (female selection rate ÷ male selection rate) on the held-out split | ≥ 0.80 | uci-statlog-german-credit · b21f3d81db8071257d5ff1deaeba1fd4303b62712e6fcc9715c7a86202cb5871 | stratified 70/30 split, seed 42 | 5ce3c9c3484d8db1ffbc67dc4f3958c9a88009a0ae92ce51e045ea6b70258bc3 |
| C2 | Accuracy on the held-out split | ≥ 0.70 | same | same | 464df2bee6b479b742306cca356ce8e4904be22cad09beb5cfee29025c1b1d31 |

## Rationale (written by the client's decision owner — illustrative)

- **C1:** The system recommends credit decisions for natural persons. We want evidence that approval rates for women are not substantially lower than for men. 0.80 is the "four-fifths" rule of thumb used in bias-audit practice; it is not a legal standard, and we use it as a floor for this acceptance round, not as proof of fairness.
- **C2:** Below 0.70 accuracy on held-out data, the recommendations would add more review work than they save. The threshold reflects our operational need, not a benchmark.

Falsify records this rationale and who approved it. Falsify does not assess whether the metric or threshold is appropriate.

## Test procedure

- Who runs the test: supplier test lead (demo signer)
- Where: supplier's environment, script `run_acceptance.py`
- Planned window: 2026-09-23
- What counts as a deviation: any change to a criterion, threshold, test data or configuration after this plan is sealed.

## Deviations

If anything in this plan changes after sealing, a new plan version is drafted with the reason for the change, signed again and sealed again. The earlier version stays in the record.

## Approvals

| Side | Signer | Role | Signature |
|---|---|---|---|
| Client decision owner | demo-client@acceptance-record.example | Head of Credit Risk (illustrative) | `1-acceptance-plan.md.client.sig` |
| Supplier responsible person | demo-supplier@acceptance-record.example | Delivery lead (illustrative) | `1-acceptance-plan.md.supplier.sig` |

The sealing record (registry receipts and timestamps) is kept outside this document, in `seal-plan.yaml`, so that sealing does not change the signed bytes.
