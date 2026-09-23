# Falsify verification statement

**Statement ID:** VS-2026-001 · **Date:** 2026-09-23 · **Issued by:** Falsify OÜ (reg. 17574308, Tallinn, Estonia)

> ILLUSTRATIVE. This statement closes an illustrative acceptance record in which Falsify OÜ plays both the supplier and the client role. It is signed with a demo key, not by a named person.

## What this statement covers

| | |
|---|---|
| Delivery | Illustrative delivery ACC-DEMO-01 |
| System version | sklearn-logistic-regression-l2-C1.0, trained by `run_acceptance.py` (SHA-256 e3d8c19d214f56acc6ce5409eda30043cb298151d8d921b1e36b4ddf00c8ed58) at seed 42 |
| Documents | Acceptance plan AP-2026-001 v1 · Acceptance report AR-2026-001 · Change and re-review conditions CR-2026-001 |

| Record | Registry hash | Registry record | Registry time (UTC) | Transparency log index |
|---|---|---|---|---|
| criteria-C1 | `5ce3c9c3484d8db1ffbc67dc4f3958c9a88009a0ae92ce51e045ea6b70258bc3` | https://registry.falsify.dev/5ce3c9c3484d8db1ffbc67dc4f3958c9a88009a0ae92ce51e045ea6b70258bc3 | 2026-09-23T11:50:23.053Z | 122162600 |
| criteria-C2 | `464df2bee6b479b742306cca356ce8e4904be22cad09beb5cfee29025c1b1d31` | https://registry.falsify.dev/464df2bee6b479b742306cca356ce8e4904be22cad09beb5cfee29025c1b1d31 | 2026-09-23T11:50:27.917Z | 122162688 |
| seal-plan | `da55fc4ac5cc572ce13ad2a913956414b186ec1685849ff1254058b78cb70cb9` | https://registry.falsify.dev/da55fc4ac5cc572ce13ad2a913956414b186ec1685849ff1254058b78cb70cb9 | 2026-09-23T11:50:42.399Z | 122163063 |
| linkage-start-C1 | `14bc38f2bd355d86457cbedba9b37a25f2da7eb57350a7e26a591ba55d09fd92` | https://registry.falsify.dev/14bc38f2bd355d86457cbedba9b37a25f2da7eb57350a7e26a591ba55d09fd92 | 2026-09-23T11:51:18.625Z | 122163511 |
| linkage-start-C2 | `2319707056303917528b9d4d20659cdd9e80d1db3e1be20c38bfc2d9946b592d` | https://registry.falsify.dev/2319707056303917528b9d4d20659cdd9e80d1db3e1be20c38bfc2d9946b592d | 2026-09-23T11:51:21.584Z | 122163513 |
| linkage-final-C1 | `86c224c760c7e1564a33693a08c3565bb9e27aebf8f149b1993c0a0344d1ebcf` | https://registry.falsify.dev/86c224c760c7e1564a33693a08c3565bb9e27aebf8f149b1993c0a0344d1ebcf | 2026-09-23T11:51:37.793Z | 122163530 |
| linkage-final-C2 | `74415372626b6e608dc2a7ea3b187e18b08b56fcb61cda1b2908f2c3f30b7517` | https://registry.falsify.dev/74415372626b6e608dc2a7ea3b187e18b08b56fcb61cda1b2908f2c3f30b7517 | 2026-09-23T11:51:41.284Z | 122163532 |
| seal-report | `86f76e446db76babca94cd97e645fafc838e0524f05bd75aa594f77ce98e7759` | https://registry.falsify.dev/86f76e446db76babca94cd97e645fafc838e0524f05bd75aa594f77ce98e7759 | 2026-09-23T11:52:20.285Z | 122164037 |

## Checks we performed (all reproducible with `VERIFY.sh`, offline)

- [x] Both criteria records hash to the values in their receipts; the test data bytes match the recorded dataset hash; the observed values in `result.json` meet the recorded thresholds (C1 0.857919 ≥ 0.80, C2 0.74 ≥ 0.70).
- [x] Each run-final record chains to its run-start record and to its criteria record.
- [x] The plan, the report and the conditions each carry two valid signatures from the keys listed in `keys/allowed_signers`.
- [x] The two seal records list the exact bytes of every signed document, signature file, `result.json` and `run_acceptance.py`.
- [x] Every registry record hash recomputes from the YAML on disk.
- [x] Every registry receipt carries a valid Ed25519 signature from the registry key (kid 34dd3fdfcf92bb13).
- [x] Every RFC 3161 timestamp verifies against the chain of the time-stamping authority (timestamp.sigstore.dev).
- [x] The independent timestamps are in this order: criteria records, signed plan, run-start records, run-final records, report seal.
- [x] The report refers to the sealed plan and to both criteria records by hash, and its thresholds match the recorded criteria.

**Missing references found:**
- No hash of the trained model artefact is recorded. The system version is identified only by the training script's hash and the seed; a reader who retrains gets the same model only if the software environment matches (the runner's environment string is in the linkage records).

## Checks we did not perform

- Whether the criteria and thresholds are appropriate for the intended purpose. The four-fifths rule used for C1 is a rule of thumb, not a legal standard.
- Whether the test results are correct beyond recomputing the verdict from `result.json`.
- Whether the tests ran after the plan was sealed. The run-start and run-final records were anchored after the plan, but the runner times inside them are the supplier's statement.
- Whether other versions, plans or test runs existed that are not in this record.
- The identity of the signers. The signatures in this example are made with demo keys generated for the illustration.
- Transparency-log inclusion proofs (available online by appending `.rekor` to each registry record).
- Whether the system or its documentation complies with the AI Act or any other law.

Also disclosed: criterion C1 repeats the configuration of our August 2026 worked example, so its value was known to us before this plan was written. This example shows the structure of the record, not a blind test.

## How to verify without us

The integrity and timestamps of the documents listed above can be verified without trusting either party's own systems, or ours. Run `./VERIFY.sh` in this directory; it needs Python 3 with PyYAML, OpenSSL 3 and OpenSSH.

## Two different signatures

- **Registry receipts** carry a technical signature made by the registry's Ed25519 key (kid 34dd3fdfcf92bb13). It shows that the registry received these bytes at that time.
- **This statement** is signed with the demo key `demo-falsify@acceptance-record.example`. In a real Pack it is signed on behalf of Falsify OÜ by a named person, and it covers only the checks listed above.

This statement was prepared with AI assistance and reviewed by Falsify OÜ.
