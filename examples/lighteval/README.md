# lighteval × PRML — one adapter, both ecosystems

Hugging Face's [lighteval](https://github.com/huggingface/lighteval) `eval`
backend is built on the UK AI Security Institute's
[Inspect](https://inspect.aisi.org.uk/) framework, and its log output is
Inspect's log schema. That convergence has a practical consequence: the
existing [falsify-inspect](https://github.com/studio-11-co/falsify-inspect)
adapter — listed in Inspect's official extensions catalog — verifies
lighteval runs **out of the box**. Lock the bar before `lighteval eval`,
verify the log it writes afterwards. No lighteval-specific code needed.

## Run it (offline)

```bash
pip install falsify-inspect
python lock_and_verify.py
```

Expected output:

```
[lock]   math_scorer <= 0.10 sealed   sha256 a96f01de2a026962…
[verify] hash_match=True observed=0.0 -> PASS
[tamper] threshold edited 0.10 -> 0.50 -> hash_match=False (TAMPERED detected)
demo OK
```

The bundled `fixture_lighteval_log.json` is a real lighteval 0.13 output
(mockllm backend, gsm8k, 4 samples). Threshold direction in the demo is
chosen so the mock model's 0.0 makes the PASS/TAMPERED mechanics visible;
it is illustrative, not a real claim.

## Live two-command flow

```bash
pip install lighteval "inspect-ai==0.3.140"   # pin: see note below
# 1. lock BEFORE the run (writes the manifest + prints the hash):
python - <<'PY'
from falsify_inspect import preregister
h, m = preregister(metric="math_scorer", threshold=0.8, threshold_direction=">=",
    dataset="openai/gsm8k", dataset_hash="<sha256 of pinned dataset revision>",
    model_version="<api>/<model>", sample_size=1, seed=0,
    pre_registered="<now, RFC3339>", inspect_task="gsm8k",
    output_path="claim.prml.yaml")
print(h, m.claim_id)
PY
# 2. run, then verify the produced log:
lighteval eval <api>/<model> "lighteval|gsm8k|0" --log-dir out
# verify_eval_log(out/logs.json'daki log, expected_hash=..., claim_id=...)
```

**Note on the pin:** as of lighteval 0.13.0 a fresh install crashes with
current inspect-ai (field renames in `GenerateConfig`); we reported it with
a fix suggestion in
[huggingface/lighteval#1327](https://github.com/huggingface/lighteval/issues/1327).
`inspect-ai==0.3.140` is the verified workaround until it lands.

## Boundary

Per PRML §8.1: the commitment proves the bar predates the run and hasn't
moved — not that the metric, dataset or result is sound. lighteval logs do
not carry a dataset content hash or seed; supply both at lock/verify time
(the adapter's documented overrides), pinning the dataset revision you
actually evaluate.
