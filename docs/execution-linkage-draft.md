# Execution Linkage — draft v0 (2026-07-31)

**Status:** non-normative draft, open for input. Prompted by the Andes
interoperability assessment (finding 3): a PRML receipt proves no-later-than
existence of the evaluation bar; it does not prove the evaluation had not
already run. Closing that gap requires linking a separately evidenced
execution to the prior receipt.

## What already exists

The MLflow adapter (`mlflow-falsify >= 0.3.0`) implements the pattern
concretely: `locked_run()` captures the manifest hash at run start, the run
context binds it as a tag, and `verify_run()` computes the verdict against
the locked bar at run end, writing `prml.verdict` / `prml.observed` back to
the run. What is missing is an adapter-independent format.

## Proposed linkage record (strawman)

A small JSON document, hashable and anchorable like a manifest:

```json
{
  "linkage_version": "prml-linkage/0",
  "manifest_hash": "<sha256 of the locked manifest>",
  "receipt": "<registry receipt URL or null>",
  "run": {
    "id": "<runner-native run identifier>",
    "started_at": "<RFC 3339, recorded at start>",
    "environment": "<free-form runner fingerprint>",
    "model_version": "<as pinned in the manifest, if any>",
    "dataset_hash": "<must equal manifest dataset.hash>"
  },
  "result": {
    "observed": <number>,
    "digest": "<sha256 of the raw result artifact>",
    "exit_code": <0|3|10|11>,
    "finished_at": "<RFC 3339>"
  }
}
```

Chronology claim: `run.started_at` after the receipt's independent
timestamp, `result.finished_at` after `run.started_at`. The linkage record
itself should be committed (or at least hashed) at run START with the
`result` block absent, then superseded at run end via `prior_hash`-style
chaining, so the start time is itself pre-committed.

## Honest limits

The runner attests its own start time; without a trusted execution
environment this is process evidence, not cryptographic proof. The linkage
makes the "already ran" attack require premeditated fabrication of the run
record before the receipt, rather than casual reordering after the fact.

## Open questions (input welcome, including from Kernal)

1. Should the start-time pre-commitment be mandatory or a strength tier?
2. Is the runner fingerprint free-form or enumerated?
3. Where does the linkage live: registry kind=linkage, or adapter-local?
