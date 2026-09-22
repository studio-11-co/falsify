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
- created_at 2026-09-22T14:40:40Z (producer-declared) · public receipt 2026-09-22T14:57:34Z (registry, RFC 3161, Rekor): https://registry.falsify.dev/2282ae19876aeb7936b4561751c857aec20dc982bf910115acee36f57a2db8fa

## 4. Data collection (phase 4)

The 4.1 pilot flagged one ambiguous translation (q001). The query was re-translated; the dataset bytes changed; the bar did not. Manifest v2 was locked before full data collection (4.2):

- `preregistration-v2.prml.yaml` → `sha256:f38e1825ae4f7ba7e6469026f054503bb6dfe0f0f3bdcb70d8af0053261de8b7` · public receipt 2026-09-22T14:57:40Z: https://registry.falsify.dev/f38e1825ae4f7ba7e6469026f054503bb6dfe0f0f3bdcb70d8af0053261de8b7
- run declared against v2: `linkage-start.yaml`, run id `prep-eval-e-run-2`, started 14:57:45.96Z · start record on the public registry at 14:57:46.44Z: https://registry.falsify.dev/4c9f2320af616b18489c099fae4f7652753c39f6d000f07a371e5e0d90bccd14

## 5. Data analysis (phase 5)

Observed `instruction_set_accuracy = 0.88` (illustrative). Verdict against the pre-registered predicate: **PASS** (exit 0). Result artefact `result.json`, digest recorded in `linkage-final.yaml` (`finished_at` 14:57:54.24Z) · final record on the public registry at 14:58:14.79Z: https://registry.falsify.dev/27d21333df989fcad6fe2bcdcc9d1d1475595cd53ea63a0ed613a93a15ed14eb

## 6. Conclusions and review (phase 6)

- 6.1 The pre-registered bar was met on the revised sample.
- 6.2 The pilot changed the data, not the criterion; that distinction is visible only because v1 was never edited.
- 6.3 In a real project the same four commits would be made by the evaluator; here they were made by us, so the times above are the registry's, the timestamp authority's and Rekor's, not ours.

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

Registry receipts (all 22 September 2026, UTC): v1 14:57:34 · v2 14:57:40 · start record 14:57:46 · final record 14:58:14. Each permalink above serves `.receipt.json` (Ed25519 signature, embedded public key), `.tsr` (raw RFC 3161 token) and `.rekor` (transparency-log inclusion proof), so the times can be checked without trusting the registry.

What the verification shows: the bar in v2 existed no later than 14:57:40 UTC and has not changed; a run against that bar was on the public record at 14:57:46, before the runner reports finishing at 14:57:54; the reported number clears the bar. What it does not show: that the number is correct, or that no earlier, unrecorded run took place. The ordering evidence is process evidence anchored in independent clocks, not proof.
