# Submission requirements (template — adapt freely)

Every submission to this benchmark must include a **pre-registered claim**:

1. **Before you run your evaluation**, write a PRML manifest
   (`your-entry.prml.yaml`, 9 fields — [spec](https://spec.falsify.dev/v0.1)):

   ```yaml
   version: prml/0.1
   claim_id: <uuidv7>
   created_at: '2026-08-01T09:00:00Z'
   metric: exact_match
   comparator: '>='
   threshold: 0.85
   dataset: {id: <benchmark-split-id>, hash: <sha256-of-split>}
   seed: 42
   producer: {id: <your-org-or-pseudonym>}   # no personal data — it is public forever
   ```

2. **Lock it publicly**: paste it at [registry.falsify.dev](https://registry.falsify.dev)
   and keep the receipt permalink. The receipt is independently timestamped —
   it proves the bar existed before your results did.

3. **Run your eval**, then open a PR adding the manifest under `submissions/`.

The gate rejects: manifests that fail PRML validation, manifests whose hash
has no public receipt, and manifests edited after locking (exit 3, TAMPERED).

**What this does NOT prove:** that your score is correct. It proves the bar
was locked first. Score verification stays with the maintainers.
