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
| 3.2 pre-register evaluation | `preregistration-v1.prml.yaml` + `.sha256` sidecar + public receipt | this manifest existed no later than the receipt time and has not changed |
| 4.1 pilot → "document all changes" | `preregistration-v2.prml.yaml` + `deviation-2026-09-22.md` | what changed (dataset bytes), what did not (the threshold) |
| 4.2 full data collection | `linkage-start.yaml` (prml-linkage/0) + public receipt | a run was declared against manifest v2, on the public record, before it finished |
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
linkage-start.yaml               prml-linkage/0 start record (run declared against v2; committed before the run finished)
linkage-final.yaml               prml-linkage/0 final record (observed 0.88, exit 0; committed after)
result.json                      the raw result artefact whose digest is in the final record
final-report.md                  the 6.4 report
run.sh                           re-verifies everything offline
```

## Run it

```bash
./run.sh
```

It recomputes both manifest hashes, checks the v2 dataset bytes against `dataset.hash`, evaluates the predicate against the observed value, and verifies the linkage chain (tier L2: final → start → manifest). No network, no account. Expected last line: `PREP-Eval example: all checks passed`.

## The public receipts

The receipts that make the timestamp independent of the producer come from the public registry. All four records in this directory are committed (22 September 2026); each receipt is Ed25519-signed by the registry, countersigned by an RFC 3161 timestamp authority, and mirrored to the Rekor transparency log.

| Record | Registry permalink | Registry time (UTC) | RFC 3161 | Rekor index |
|---|---|---|---|---|
| manifest v1 | [2282ae19…2db8fa](https://registry.falsify.dev/2282ae19876aeb7936b4561751c857aec20dc982bf910115acee36f57a2db8fa) | 2026-09-22 14:57:34.816 | 14:57:35 | 120937935 |
| manifest v2 | [f38e1825…de8b7](https://registry.falsify.dev/f38e1825ae4f7ba7e6469026f054503bb6dfe0f0f3bdcb70d8af0053261de8b7) | 2026-09-22 14:57:40.168 | 14:57:40 | 120937972 |
| linkage start (run `prep-eval-e-run-2`) | [4c9f2320…ccd14](https://registry.falsify.dev/4c9f2320af616b18489c099fae4f7652753c39f6d000f07a371e5e0d90bccd14) | 2026-09-22 14:57:46.437 | 14:57:46 | 120938028 |
| linkage final | [27d21333…d14eb](https://registry.falsify.dev/27d21333df989fcad6fe2bcdcc9d1d1475595cd53ea63a0ed613a93a15ed14eb) | 2026-09-22 14:58:14.787 | 14:58:15 | 120938456 |

Two separate statements, because they rest on different evidence:

- **Offline verification (`run.sh`): tier L2.** The final record chains to the start record, both match manifest v2, the dataset bytes match, the verdict recomputes. No network is used, so no anchor time is checked and no higher tier is claimed.
- **Registry-checked ordering (done by hand, from the table above):** anchor(v1) 14:57:34.8 < anchor(v2) 14:57:40.2 < anchor(start) 14:57:46.4. The runner itself reports `started_at` 14:57:45.96 and `finished_at` 14:57:54.24. So the start record, carrying v2's hash, was on third-party clocks 476 ms *after* the runner says it started and 8 s *before* the runner says it finished. prml-linkage/0 §5 defines tier L3 as the start record "anchored before the run completes", which this satisfies; its §4 check 8 instead asks for `anchor(S) ≤ started_at` within a declared tolerance, which this misses by 476 ms with no tolerance declared. The draft is inconsistent on that point (noted in its §7); until it is settled we do not call this L3.

Trust assumptions, stated: the anchor times come from the registry, an RFC 3161 authority and the Rekor log, none of them ours to move. `started_at` and `finished_at` come from the runner, which is us. What the anchors establish is that these exact records existed by those times. They do not establish that the evaluation actually ran between them: a producer who ran first, looked, and then performed the whole lock → start → finish ceremony is not detectable by linkage alone (§6 of the draft says so).

Append `.receipt.json`, `.tsr` or `.rekor` to a permalink for the signed receipt, the raw RFC 3161 token, or the Rekor inclusion proof. A reader who reaches the same conclusions from those files without our help is the test this example has not yet passed.

To commit your own:

```bash
curl -X POST https://registry.falsify.dev/commit -H "content-type: text/yaml" --data-binary @preregistration-v1.prml.yaml
# sealed variant (bar withheld until you reveal it): add -H "X-PRML-Sealed: 1"
```

## What this shows, and what it does not

- A PRML receipt shows that **this exact bar existed no later than time T and has not changed since**. It does not, by itself, show that the run happened after T.
- The linkage records add an **ordering claim** (lock → run → result) at a stated tier. Without trusted execution hardware, a runner's start time is process evidence, not cryptographic proof. The specification says so; this example does too.
- Nothing here shows the **result is correct**. Score verification stays with the evaluator and the reader.

Three ways a producer could still mislead, and how the workflow handles each:

1. **Run first, look, then lock a bar the number clears.** Not caught by a receipt alone. Narrowed, not closed, by anchoring the start record before the run completes: the forgery then has to be premeditated before the anchor. This directory anchored its start record 8 s before the runner-reported finish (see "The public receipts" for exactly what that does and does not establish); `finished_at` is still the runner's own word.
2. **Lock many manifests, report the one that passed.** Not prevented. The registry is public and receipts carry `producer.id`; the party relying on the report should ask for the producer id and look at sibling receipts, and the acceptance owner can require one manifest per evaluation in the project plan (3.1).
3. **Keep the threshold, change the grader or the scoring instructions.** Caught only if the grader is part of what was hashed. PRML's required fields cover the metric name, the test items (`dataset.hash`) and the seed; a grader prompt is not a required field. Put grader instructions inside the dataset artefact, or record them in a separate manifest, and say which one the report relies on.

## References

- Carro, M. V., Burnell, R., Mougan, C., Reuel, A., Schellaert, W., Salaudeen, O. E., Zhou, L., Paskov, P., Cohn, A. G., Hernández-Orallo, J. *PREP-Eval: A Pre-registration and REporting Protocol for AI Evaluations*, v1.0, manuscript under review. https://prep-eval.github.io/prep-eval/
- PRML v0.1 specification: https://spec.falsify.dev/v0.1 · execution linkage draft: `spec/linkage/prml-linkage-0.md` (Draft 0, non-normative).

License of this directory: same as the repository (MIT). The PREP-Eval text quoted above is the authors'.
