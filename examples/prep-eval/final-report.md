# Final report (PREP-Eval phase 6.4) — illustrative

**Evaluation:** instruction-set accuracy of an LLM customer-service agent on the CPHOS-style sample (scaffold: PREP-Eval Appendix E).
**Status:** worked example; the dataset is a stand-in and the observed value is illustrative. The verification section is real.

## 1. Goals and objectives (phase 1)

Determine whether the agent answers or routes customer queries correctly against the internal guide files and system actions. Success criterion, as pre-registered: `instruction_set_accuracy >= 0.85` on the fixed sample, seed 7.

## 2. Evaluation design (phase 2)

Automated scoring of each answer against the expected action or answer, binary correct/incorrect, on the five-item sample. (Appendix E's design uses GPT-4-based verification plus human checks; the mechanism is unchanged by this example.)

## 3. Project plan and pre-registration (phase 3)

Manifest v1 locked before any data collection:

- `preregistration-v1.prml.yaml` → `sha256:2282ae19876aeb7936b4561751c857aec20dc982bf910115acee36f57a2db8fa`
- created_at 2026-09-22T14:40:40Z (producer-declared; a registry receipt would add an independent time)

## 4. Data collection (phase 4)

The 4.1 pilot flagged one ambiguous translation (q001). The query was re-translated; the dataset bytes changed; the bar did not. Manifest v2 was locked before full data collection (4.2):

- `preregistration-v2.prml.yaml` → `sha256:f38e1825ae4f7ba7e6469026f054503bb6dfe0f0f3bdcb70d8af0053261de8b7`
- run declared against v2: `linkage-start.yaml`, run id `prep-eval-e-run-1`

## 5. Data analysis (phase 5)

Observed `instruction_set_accuracy = 0.88` (illustrative). Verdict against the pre-registered predicate: **PASS** (exit 0). Result artefact `result.json`, digest recorded in `linkage-final.yaml`.

## 6. Conclusions and review (phase 6)

- 6.1 The pre-registered bar was met on the revised sample.
- 6.2 The pilot changed the data, not the criterion; that distinction is visible only because v1 was never edited.
- 6.3 Next step in a real project: commit v1, v2 and the start record to the public registry so that the times are not the producer's own.

### 6.4 Deviations from the pre-registered plan

| Deviation | Reason | Effect on the bar | Record |
|---|---|---|---|
| Dataset q001 re-translated (v1 → v2) | phase 4.1 pilot flagged an ambiguous rendering | none: metric, comparator, threshold, seed unchanged | `deviation-2026-09-22.md` |

No other deviations.

## Verification

Anyone with this directory can check every claim above without contacting us:

```bash
./run.sh
```

which performs, in order: recompute the v1 and v2 manifest hashes against the sidecars; recompute the v2 dataset hash against `dataset.hash`; evaluate `0.88 >= 0.85`; verify the linkage chain final → start → manifest (tier L2).

Registry receipts: none at the time of writing (the manifests are not committed). If committed, the receipt URLs go here, and the reader gains an RFC 3161 time and a Rekor log entry for each record.

What the verification shows: the bar in v2 existed no later than its lock time and has not changed; the run was declared against that bar; the reported number clears it. What it does not show: that the number is correct, or that no run happened before the lock (tier L2 is process evidence for ordering, not proof).
