# falsify-verify

GitHub Action that verifies [PRML v0.1](https://spec.falsify.dev/v0.1) manifests in your repository on every push, pull request, or scheduled run.

## What it does

1. Walks your repo for files matching `**/*.prml.yaml` (configurable).
2. For each manifest:
   - Re-canonicalizes the YAML (lexicographic key order, 2-space indent, LF terminators, UTF-8).
   - Computes SHA-256 of the canonical bytes.
   - Compares against the sidecar hash file `<name>.prml.sha256`.
3. Fails CI if any manifest has a hash mismatch (TAMPERED) or, optionally, a verifier FAIL.
4. Writes a job-summary panel showing PASS / TAMPERED / missing-sidecar counts.

## Why you would use this

If your repo publishes ML accuracy claims (model cards, paper supplementary, regulatory submissions), this action ensures **the claim hash committed to git matches the claim being shipped**. Any silent edit to a `.prml.yaml` after lock-time produces a TAMPERED CI failure.

For EU AI Act Article 12 logging or Article 18 retention, this gives you a CI-enforced integrity floor.

## Usage

Add this to `.github/workflows/falsify-verify.yml`:

```yaml
name: PRML Manifest Verification

on:
  push:
    paths:
      - '**/*.prml.yaml'
      - '**/*.prml.sha256'
  pull_request:
    paths:
      - '**/*.prml.yaml'
      - '**/*.prml.sha256'

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Verify PRML manifests
        uses: studio-11-co/falsify/.github/actions/falsify-verify@main
```

For a published version once we cut a release tag:

```yaml
      - uses: studio-11-co/falsify-verify@v0.1
```

## Inputs

| Name | Default | Description |
|---|---|---|
| `manifest-glob` | `**/*.prml.yaml` | Glob pattern to locate manifests. |
| `fail-on-tampered` | `true` | Exit 1 when any sidecar hash mismatch is detected. |
| `fail-on-falsified` | `true` | Exit 1 when verifier emits exit code 10 (claim FAIL). v0.1 hash-only mode does not exercise this; v0.2 will. |
| `python-version` | `3.12` | Python version to run under. |

## Outputs

| Name | Description |
|---|---|
| `manifests-checked` | Total number of manifests found and processed. |
| `tampered-count` | Count of manifests with sidecar hash mismatch. |
| `falsified-count` | Count of manifests whose claim verified to FAIL. |
| `pass-count` | Count of manifests whose hash matched the sidecar. |

## What v0.1 does NOT do

- **Does not execute the claim.** Verification of a claim requires the dataset and model, which are not in the manifest. v0.1 verifies hash integrity only. v0.2 will add an `execute` mode that runs `falsify verify` against a configured dataset path.
- **Does not check `prior_hash` chain integrity across the repo.** It validates each manifest individually. A future `falsify-audit` action will validate forward-only chain semantics.
- **Does not sign manifests.** Producer signatures are an optional v0.1 field and a mandatory v0.2 field. CI signing integration will be added when v0.2 ships.

## Example output (job summary)

```
## falsify-verify

Manifests checked: 3
- ✅ Hash verified: 2
- ❌ Tampered: 1
- ⚠️ Missing sidecar: 0

### Tampered manifests

| Manifest | Sidecar hash (first 16) | Recomputed hash (first 16) |
|---|---|---|
| claims/release-2026-q3.prml.yaml | a1b2c3d4e5f60718 | 7a8b9c0d1e2f3a4b |

---

Verified against PRML v0.1 — https://spec.falsify.dev/v0.1
```

## Limitations

- Requires `pyyaml`. The action installs it automatically.
- Sidecar discovery uses both `name.prml.yaml → name.prml.sha256` (correct convention) and `name.prml.yaml → name.sha256` (legacy fallback). Stick to the first form.
- The action runs on `ubuntu-latest`. macOS / Windows runners are untested for v0.1.

## Reporting issues

If the action fails on a manifest you believe is correct, file an issue at https://github.com/studio-11-co/falsify/issues with:

1. The manifest content (redact sensitive fields).
2. The sidecar hash.
3. The hash this action recomputed (printed in the action log).
4. The output of `python3 spec/test-vectors/v0.1/generate.py` from the same Python version.

If the recomputed hash matches `falsify` CLI's output but disagrees with the action, that's a bug in this action. If they all disagree with the test vectors, that's a v0.1 spec ambiguity and warrants a v0.2 amendment.

## License

Action code: MIT (matches `falsify` reference implementation).
PRML specification: Community Specification License 1.0.
