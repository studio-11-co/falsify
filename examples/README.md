# examples/

This directory holds inputs for **two different tools** that ship in the same
package. Picking the wrong one is the single most common way to get an
`exit 2` here, so start with this table.

| You want to… | File to copy | Command |
|---|---|---|
| Commit evaluation criteria as a PRML manifest | `falsify init my-claim.prml.yaml` writes one | `falsify lock` / `falsify verify` |
| See a complete, working PRML manifest | [`first-manifest/accuracy.prml.yaml`](first-manifest/) | `falsify lock examples/first-manifest/accuracy.prml.yaml` |
| Drive the pre-registration **workflow engine** | [`template.yaml`](template.yaml) | `falsify-engine init <name>`, then `lock <name>` |
| Follow a full **pre-registration → deviation → final report** cycle (PREP-Eval phases 3.2 to 6.4), verifiable offline | [`prep-eval/`](prep-eval/) | `examples/prep-eval/run.sh` |

## The two tools

- **`falsify`** → `falsify_prml.py`. The PRML reference implementation. Reads a
  PRML manifest (`version`, `claim_id`, `created_at`, `metric`, `comparator`,
  `threshold`, `dataset`, `seed`, `producer`), canonicalizes it and takes its
  SHA-256. This is what the specification, the conformance vectors and the other
  three reference implementations are about.
- **`falsify-engine`** → `falsify.py`. A workflow CLI with its own, unrelated
  schema (`claim`, `falsification.failure_criteria`, …). It is not PRML and its
  files will not validate as PRML.

`template.yaml` belongs to the second tool. Everything else in this table
belongs to the first.

Note that `falsify-engine lock` takes a **claim name**, not a file path: it reads
`.falsify/<name>/spec.yaml`, which `falsify-engine init <name>` scaffolds. `falsify
lock` (PRML) takes a **file path**. The two tools differ here as well.

## Integration examples

The remaining subdirectories (`deepeval/`, `lighteval/`, `lm-eval-harness/`,
`mastra/`, `promptfoo/`, `opik/`, `langfuse/`, `braintrust/`, `hud/`,
`moonshot/`, `laminar/`, `cyclonedx-attestation/`, `require-receipt/`, …) each
carry their own README and show PRML alongside one host tool. `prep-eval/` is
different in kind: it shows PRML alongside a *process protocol* (PREP-Eval),
from pre-registration through a documented deviation to the final report.
