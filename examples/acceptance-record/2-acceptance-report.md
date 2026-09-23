# Acceptance test report

**Report ID:** AR-2026-001 · **Date of report:** 2026-09-23

> ILLUSTRATIVE. Falsify OÜ plays both the supplier and the client role, on public data. Not a client engagement. Signatures are made with demo keys, not by real persons.

## What this report refers to

| | |
|---|---|
| Acceptance plan | AP-2026-001 v1 · plan seal record https://registry.falsify.dev/da55fc4ac5cc572ce13ad2a913956414b186ec1685849ff1254058b78cb70cb9 |
| Criteria records | C1 https://registry.falsify.dev/5ce3c9c3484d8db1ffbc67dc4f3958c9a88009a0ae92ce51e045ea6b70258bc3 · C2 https://registry.falsify.dev/464df2bee6b479b742306cca356ce8e4904be22cad09beb5cfee29025c1b1d31 |
| System version tested | sklearn-logistic-regression-l2-C1.0, trained by `run_acceptance.py` (SHA-256 e3d8c19d214f56acc6ce5409eda30043cb298151d8d921b1e36b4ddf00c8ed58) at seed 42 |
| Actual test window | 2026-09-23, 11:51 UTC (runner times in the linkage records; the runner is the supplier) |
| Test run evidence | `result.json` SHA-256 70e2fd7f287dde840e5a5dadefe56fe9a67da8056ed10366dd47c2cfec8273ff · linkage final records C1 https://registry.falsify.dev/86c224c760c7e1564a33693a08c3565bb9e27aebf8f149b1993c0a0344d1ebcf · C2 https://registry.falsify.dev/74415372626b6e608dc2a7ea3b187e18b08b56fcb61cda1b2908f2c3f30b7517 |

This report covers the system version and test round named above only.

## Results

| Criterion | Pass if (from sealed plan) | Observed | Result | Evidence |
|---|---|---|---|---|
| C1 impact ratio (sex) | ≥ 0.80 | 0.857919 | PASS | `result.json`, linkage final C1 |
| C2 accuracy | ≥ 0.70 | 0.74 | PASS | `result.json`, linkage final C2 |

A failing result would be recorded exactly as it came out.

## Deviations from the plan

None.

## Acceptance decision

- [x] Accepted
- [ ] Accepted with conditions
- [ ] Rejected

## Signatures (responsible persons)

| Side | Signer | Role | Signature |
|---|---|---|---|
| Supplier test lead | demo-supplier@acceptance-record.example | Delivery lead (illustrative) | `2-acceptance-report.md.supplier.sig` |
| Client decision owner | demo-client@acceptance-record.example | Head of Credit Risk (illustrative) | `2-acceptance-report.md.client.sig` |

Where the AI Act applies to a system, a report like this is laid out so it can be filed with the technical documentation as a dated and signed test report (Annex IV, point 2(g)). Whether and how that applies is for the provider to determine.

## Note from Falsify

This report is the parties' document. Falsify seals its hash in `seal-report.yaml` and links it to the plan record and the tested system version. Falsify does not certify its content.
