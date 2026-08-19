# Project Moonshot (AI Verify) + PRML: lock the bar before the safety gate runs

[Project Moonshot](https://github.com/aiverify-foundation/moonshot-cicd) is
IMDA's AI safety evaluation tool, built to gate CI/CD pipelines; its results
feed the [AI Verify Testing Framework](https://aiverifyfoundation.sg/what-is-ai-verify/)
and become compliance reports. That makes its run records unusually
load-bearing — and makes one absence unusually visible: **nothing in the record
binds the bar.**

What we verified before writing this (moonshot-cicd v1.1.0; main repo also
checked):

- `TestConfigEntity` binds name, type, dataset, metric, attack module and
  prompt — and **no comparator, no threshold, no seed, no dataset content
  hash**.
- The metric adapters aggregate to rates (`exact_string_match`,
  `attack_success_rate`); there is no pass/fail gate and no gating exit code
  in the CLI.
- The main `moonshot` repo *does* have a bar concept — recipes carry a
  `grading_scale` (A–E bands) — but it lives in an editable JSON field with no
  lock, no digest, and nothing showing the scale predates the run.

So the claim is narrow and honest: a bar either does not exist in the config
(moonshot-cicd) or exists without tamper evidence (moonshot). In both cases,
nothing ties a run to the bar that was in force when it started.

[PRML](https://spec.falsify.dev) locks exactly that.

## What the bridge does

```
lock    before: manifest binds the aggregate key Moonshot really emits
        (exact_string_match, 0–100), comparator + threshold,
        sha256(canonical JSON of the items), seed
run     Moonshot's own machinery, imported not imitated: the real
        AccuracyAdapter (judge-free exact match) over real
        MetricIndividualEntity objects, aggregated by the real get_results
verify  after: the aggregated rate vs the pre-locked bar
        exit 0 PASS · 10 FAIL · 3 TAMPERED
```

## Run it

```sh
git clone https://github.com/aiverify-foundation/moonshot-cicd
pip install falsify pydantic rich pyyaml
cd moonshot-cicd   # the tool resolves its config relative to the repo root
PYTHONPATH=./src python3 ../moonshot_prml.py
```

Expected output ends with a PASS verdict and a caught tamper attempt:

```
observed exact_string_match = 75.0  vs locked bar >= 70.0
verdict: PASS

-- adversarial: threshold edited 70.0 -> 50.0 AFTER the run --
verdict: TAMPERED — manifest does not match the pre-run lock
```

## What is real vs modelled

- **Scoring: real moonshot-cicd code.** The run goes through Moonshot's own
  config loading (`moonshot_config.yaml`, `LocalStorageAdapter`), the real
  `AccuracyAdapter.get_individual_result`
  (`entity.target == entity.predicted_result.response` — no judge), and the
  real `get_results` aggregation. Verified against moonshot-cicd v1.1.0 in a
  clean environment; all three verdict paths exercised.
- **PRML side: real `falsify` reference** (canonical bytes, manifest hash,
  verdict codes).
- **Not exercised: the LLM connector.** Moonshot's connectors all require a
  live endpoint (OpenAI/Anthropic/AWS); the application-under-test's outputs
  are supplied as recorded responses, exactly as a CI replay would. The
  lock/verify split is unchanged with a live connector — the manifest never
  depends on where the outputs came from.

Why this host matters more than most: Moonshot's output is not a dashboard
number, it is compliance evidence by design. A gate whose results are quoted
to auditors is precisely where "the bar predates the result" needs to be
checkable rather than asserted.
