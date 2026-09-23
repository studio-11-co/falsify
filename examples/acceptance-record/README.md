# A completed acceptance record — illustrative

**Status: illustrative.** Falsify OÜ plays both the supplier and the client role, on public data (UCI Statlog German Credit). This is not a client engagement. The signatures are made with demo keys generated for this example, not by real persons. Criterion C1 repeats the configuration of our August 2026 worked example, so its value was known to us before the plan was written: this directory shows the structure of an acceptance record, not a blind test.

It is what an Acceptance Evidence Pack delivers for one acceptance round: the documents that support one acceptance decision, linked to each other and to independent timestamps, so that someone reviewing the decision later can see who approved what, and which result rests on which plan. The integrity and timestamps of the documents can be verified without trusting either party's own systems, or ours.

## The record, in the order it was made (23 Sep 2026, UTC)

| Time (RFC 3161) | Step | Files |
|---|---|---|
| 11:50:23 · 11:50:28 | Acceptance criteria C1 and C2 recorded as PRML manifests | `criteria-C1.prml.yaml`, `criteria-C2.prml.yaml` |
| 11:50:42 | Acceptance plan signed by both sides and sealed | `1-acceptance-plan.md` + `.client.sig`, `.supplier.sig` · `seal-plan.yaml` |
| 11:51:18 · 11:51:21 | Test runs declared against the criteria (run-start records) | `linkage-start-C1.yaml`, `linkage-start-C2.yaml` |
| 11:51:37 · 11:51:41 | Results recorded (run-final records) | `result.json`, `linkage-final-C1.yaml`, `linkage-final-C2.yaml` |
| 11:52:20 | Acceptance report and change conditions signed and sealed | `2-acceptance-report.md`, `3-change-and-rereview.md` + signatures · `seal-report.yaml` |
| 11:55:31 | Falsify verification statement signed and sealed | `4-verification-statement.md` + `.falsify.sig` · `seal-statement.yaml` |

Every step above has a public registry record with a signed receipt, an RFC 3161 timestamp from timestamp.sigstore.dev and a Rekor transparency-log entry. The receipts are in `receipt-*.json`, the timestamp tokens in `anchors/`.

Results: C1 impact ratio (sex) 0.857919 against ≥ 0.80 — pass. C2 accuracy 0.74 against ≥ 0.70 — pass. Decision: accepted.

## Verify it

```bash
./VERIFY.sh
```

Needs Python 3 with PyYAML, OpenSSL 3 (the LibreSSL shipped with macOS cannot verify these timestamp tokens; install `openssl@3`), and OpenSSH 8 or later. No network is used. Eight checks: criteria hashes and verdicts, linkage chains, document signatures, seal records, registry hashes, registry receipt signatures, RFC 3161 timestamps, and the order of the timestamps.

## Who did what

| Party | In this example | In a real Pack |
|---|---|---|
| Client and supplier | Falsify OÜ plays both | The client and the delivery team write the criteria, the rationale, the test results and the decision, and sign with their own e-signature tools |
| Falsify | Packaged the documents, recorded and sealed them, linked them, listed a missing reference, issued the statement | The same |

Arranging a document is not vouching for its content.

## What this shows, and what it does not

- The criteria and the signed plan existed no later than 11:50:42 UTC and have not changed since. The run-start records were anchored after that, and the report after the run-final records.
- It does not show that the criteria are appropriate, that the results are correct, or that the tests ran after the plan. The runner times inside the linkage records are the supplier's statement.
- It does not show that no other plan or run existed. A reviewer should ask for the producer id (`acceptance-record-example.falsify`) and look at its other records.
- Missing reference, listed in the statement: no hash of the trained model artefact is recorded; the system version is identified by the training script's hash and the seed.

## Files

```
criteria-C1.prml.yaml, criteria-C2.prml.yaml     acceptance criteria (PRML v0.1) + .sha256 sidecars
1-acceptance-plan.md (+ 2 signatures)            plan, rationale, approvals
2-acceptance-report.md (+ 2 signatures)          results and decision
3-change-and-rereview.md (+ 2 signatures)        agreed change and re-review conditions (recorded, not monitored)
4-verification-statement.md (+ signature)        checks performed and not performed
seal-plan.yaml, seal-report.yaml, seal-statement.yaml   hashes of the signed bytes, each anchored in the registry
linkage-start-C*.yaml, linkage-final-C*.yaml      prml-linkage/0 run records (draft)
run_acceptance.py, result.json, german.data       the test and its output
receipt-*.json, anchors/                          registry receipts, RFC 3161 tokens, TSA chain, registry public key
keys/allowed_signers                              demo public keys (private keys are not published)
VERIFY.sh                                         offline verification
```

License: MIT, same as the repository. German Credit data: Hofmann, H. (1994), Statlog (German Credit Data), UCI Machine Learning Repository, https://doi.org/10.24432/C5NC77, CC BY 4.0.
