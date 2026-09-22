# PREP-Eval × PRML — a worked example

**Phase 3.2 (pre-register the evaluation) → phase 4.1 deviation → phase 6.4 (final report), with every step verifiable offline.**

Status: illustrative. [PREP-Eval](https://prep-eval.github.io/prep-eval/) (Carro, Burnell, Mougan, Reuel, Schellaert, Salaudeen, Zhou, Paskov, Cohn, Hernández-Orallo; v1.0, manuscript under review) is a 64-page process protocol for AI evaluations. It does not mention PRML, and nothing here is endorsed by its authors. This directory is our reading of how the two fit: PREP-Eval says *what* to record and *when*; PRML gives the record a form that anyone can verify later without trusting the repository it was stored in.

## Why the two fit

PREP-Eval, task list 3.2.1:

> Select an appropriate time-stamped repository or version control system for submission … Submit a "pre-registration" of the protocol with sections 1, 2 and 3.1.

And task list 6.4.1:

> Document and explain any deviations from the pre-registered plan. Upload the final report to the designated repository or registry.

The protocol leaves the timestamp to the repository (it names the Open Science Framework as an example). A reader of the final report therefore has to trust that repository's clock and its integrity. A PRML manifest is the same commitment in a form with a different trust profile: nine required fields, canonical bytes, one SHA-256. Anyone holding the manifest text can recompute the hash with a standard library. If the hash is also committed to the public registry, the record carries an Ed25519 signature, an RFC 3161 timestamp and a Rekor transparency-log entry, and the reader no longer needs the producer's or the repository's word for *when* it existed.

## The case: PREP-Eval Appendix E

Appendix E of the paper walks a real evaluation (CHOPS, an LLM customer-service agent, Shi et al. 2024) through phases 1 to 3. Its own closing line, E.3.2:

> The protocol declaration was not publicly registered after the design of the evaluation.

So the appendix has everything a pre-registration needs except the registration. We take its metric names from E.1.2 (`instruction_set_accuracy`, guiding-file accuracy, characters per question) and write the first of them as a PRML manifest. Two honest notes:

- **The threshold is ours.** Appendix E states a comparative goal ("outperforms the baselines"), not a numeric acceptance criterion. PRML's required `threshold` field forces that decision to be made, and written down, before the run. `0.85` is illustrative.
- **The dataset is a stand-in.** `cphos-en-sample.jsonl` is five synthetic lines in the style of the CPHOS case, so that `dataset.hash` is a real hash of real bytes you can recompute. It is not the CPHOS dataset.

## Mapping

| PREP-Eval | Artefact here | What a later reader can check |
|---|---|---|
| 1.2 technical objectives, success criteria | `metric`, `comparator`, `threshold` in the manifest | the exact bar, byte for byte |
| 2.3 analysis specification (data, estimator) | `dataset.id`, `dataset.hash`, `seed` | the test items and seed the bar referred to |
| 3.2 pre-register evaluation | `preregistration-v1.prml.yaml` + `.sha256` sidecar (+ registry receipt, optional) | this manifest existed no later than the receipt time and has not changed |
| 4.1 pilot → "document all changes" | `preregistration-v2.prml.yaml` + `deviation-2026-09-22.md` | what changed (dataset bytes), what did not (the threshold) |
| 4.2 full data collection | `linkage-start.yaml` (prml-linkage/0) | a run was declared against manifest v2 before it finished |
| 5.2 planned analysis | `linkage-final.yaml`, `result.json` | observed value, result digest, verdict, chained to the start record |
| 6.4 complete the registration | `final-report.md` | the report cites hashes, not adjectives |

## Files

```
cphos-en-sample.jsonl            illustrative dataset (v1 bytes)
cphos-en-sample-v2.jsonl         same, one query re-translated after the pilot (v2 bytes)
preregistration-v1.prml.yaml     phase 3.2 manifest        sha256 2282ae19…2db8fa
preregistration-v2.prml.yaml     revised manifest           sha256 f38e1825…de8b7
*.prml.prml.sha256               sidecars written by `falsify lock`
deviation-2026-09-22.md          the 6.4 deviation record, both hashes side by side
linkage-start.yaml               prml-linkage/0 start record (run declared against v2)
linkage-final.yaml               prml-linkage/0 final record (observed 0.88, exit 0)
result.json                      the raw result artefact whose digest is in the final record
final-report.md                  the 6.4 report
run.sh                           re-verifies everything offline
```

## Run it

```bash
./run.sh
```

It recomputes both manifest hashes, checks the v2 dataset bytes against `dataset.hash`, evaluates the predicate against the observed value, and verifies the linkage chain (tier L2: final → start → manifest). No network, no account. Expected last line: `PREP-Eval example: all checks passed`.

## Publishing the commitment (optional, not done in this directory)

The receipts that make the timestamp independent of the producer come from the public registry:

```bash
curl -X POST https://registry.falsify.dev/commit -H "content-type: text/yaml" --data-binary @preregistration-v1.prml.yaml
# sealed variant (bar withheld until you reveal it): add -H "X-PRML-Sealed: 1"
```

At the time of writing, the manifests in this directory have **not** been committed to the registry; the example is complete offline. If they are committed later, the receipt URLs belong in `final-report.md`, section "Verification".

## What this shows, and what it does not

- A PRML receipt shows that **this exact bar existed no later than time T and has not changed since**. It does not, by itself, show that the run happened after T.
- The linkage records add an **ordering claim** (lock → run → result) at a stated tier. Without trusted execution hardware, a runner's start time is process evidence, not cryptographic proof. The specification says so; this example does too.
- Nothing here shows the **result is correct**. Score verification stays with the evaluator and the reader.

Three ways a producer could still mislead, and how the workflow handles each:

1. **Run first, look, then lock a bar the number clears.** Not caught by a receipt alone. Caught, at tier L3, if the start record is committed to the registry before the run finishes, because the start record carries the manifest hash and the registry's time.
2. **Lock many manifests, report the one that passed.** Not prevented. The registry is public and receipts carry `producer.id`; the party relying on the report should ask for the producer id and look at sibling receipts, and the acceptance owner can require one manifest per evaluation in the project plan (3.1).
3. **Keep the threshold, change the grader or the scoring instructions.** Caught only if the grader is part of what was hashed. PRML's required fields cover the metric name, the test items (`dataset.hash`) and the seed; a grader prompt is not a required field. Put grader instructions inside the dataset artefact, or record them in a separate manifest, and say which one the report relies on.

## References

- Carro, M. V., Burnell, R., Mougan, C., Reuel, A., Schellaert, W., Salaudeen, O. E., Zhou, L., Paskov, P., Cohn, A. G., Hernández-Orallo, J. *PREP-Eval: A Pre-registration and REporting Protocol for AI Evaluations*, v1.0, manuscript under review. https://prep-eval.github.io/prep-eval/
- PRML v0.1 specification: https://spec.falsify.dev/v0.1 · execution linkage draft: `spec/linkage/prml-linkage-0.md` (Draft 0, non-normative).

License of this directory: same as the repository (MIT). The PREP-Eval text quoted above is the authors'.
