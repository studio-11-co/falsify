# require-receipt — make PRML receipts a precondition

For operators of leaderboards, benchmarks, model marketplaces, and review
processes: a copy-paste gate that refuses any submission whose evaluation
bar was not publicly locked before the run.

- `gate.yml` — the GitHub Actions workflow (place in `.github/workflows/`)
- `SUBMISSION.md` — requirements template for your contributors

Why demand this: self-imposed pre-registration only constrains the honest.
When the *venue* requires the receipt, the constraint binds everyone who
wants in — that is the point of a gate.

Full pattern write-up: https://falsify.dev/require/
