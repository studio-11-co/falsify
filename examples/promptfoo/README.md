# promptfoo + PRML: lock the config's bar before `promptfoo eval` runs

[promptfoo](https://github.com/promptfoo/promptfoo) is unusually honest among
eval tools: the success criteria live in one YAML file, in the open — asserts,
thresholds, test cases. But that file is exactly as editable after the run as
before it. The results JSON records what passed; nothing records that the
asserts it passed against are the asserts that existed before the outputs were
known. Loosen one `equals`, or delete the one failing test and re-run, and the
report looks identical.

[PRML](https://spec.falsify.dev) locks exactly that: the success criteria,
committed to a SHA-256 over canonical bytes **before** the run, independently
verifiable offline afterwards.

## What the gate does

```
lock    before: sha256 over canonical JSON of the config's `tests` (cases AND
        asserts — the bar), bound into a PRML manifest with the pass-rate
        threshold you commit to
run     `promptfoo eval`, for real — the echo provider keeps this demo
        deterministic and offline; swap in any real provider freely
verify  after: pass rate vs the locked threshold, AND the config's tests
        re-hashed — a bar edited after locking is TAMPERED even if the
        re-run "passes"
        exit 0 PASS · 10 FAIL · 3 TAMPERED
```

## Run it

```sh
npm install promptfoo falsify-js
node prml_gate.mjs
```

Expected output ends with a PASS and two caught tamper attempts:

```
observed pass_rate = 0.75  vs locked bar >= 0.7
verdict: PASS

-- adversarial 1: threshold edited 0.7 -> 0.5 AFTER the run --
verdict: TAMPERED — manifest does not match the pre-run lock

-- adversarial 2: the failing test deleted from the config, eval RE-RUN --
   (doctored config really re-run: pass_rate = 1)
verdict: TAMPERED — the config's tests/asserts changed after locking
```

The second tamper is the promptfoo-specific one, and it is not simulated: the
gate deletes the failing test, genuinely re-runs `promptfoo eval`, gets a
perfect score — and the verdict is still TAMPERED, because the tests being
scored are no longer the tests that were locked.

## What is real

Everything. A real `promptfoo eval` subprocess end to end (verified against
promptfoo 0.122.0 from npm — no mocked scores, no sample output, no API key:
the `echo` provider is deterministic), and the real `falsify-js` reference
(0.1.12) for canonical bytes, manifest hash and verdicts. promptfoo exits 100
when any test fails; the gate treats that as a result, not an error — the
verdict on the run belongs to the locked bar, not to the exit code.

In CI, the same split pairs naturally with promptfoo's own GitHub Action:
lock in one step, eval in the next, verify in the last — and the manifest can
ride any SLSA/in-toto pipeline as an attestation predicate.
