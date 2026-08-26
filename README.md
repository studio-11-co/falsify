<img src="brand/lockup.svg" alt="falsify" width="320">

**ML evaluation claims should be locked before the experiment runs, not reported after.**

PRML commits a claim — metric, threshold, dataset hash, seed — as a SHA-256 manifest. Run the eval. The hash either matches or it doesn't.

```bash
$ pip install falsify
$ falsify lock claim.prml.yaml
locked: claim.prml.yaml
  sha256:          c30dba8e0f566d1beebf4f8d468e6e07c821f0c72562dfb64ddf6596796f7797

$ falsify verify claim.prml.yaml --observed 0.934
PASS  metric=accuracy  observed=0.934  >=  threshold=0.9

# spec edited after locking → hash no longer matches:
$ falsify verify claim.prml.yaml --observed 0.934
TAMPERED  (exit 3)
```

No install? Verify any manifest in-browser at [registry.falsify.dev](https://registry.falsify.dev). Byte-equivalent reference CLIs also ship for JS (`npm i -g falsify-js`), Go, and Rust.

4 reference implementations (Python, JavaScript, Go, Rust) byte-equivalent on all 21 conformance vectors (13 v0.1 stable + 8 v0.2). PRML v0.2 frozen 2026-05-22. The same day, Lock #2 (a public hypothesis on the spec's own distribution, target ≥3 external contributors in 14 days) resolved at 0/3. The mechanism worked, the post-mortem is at [falsify.dev/notes/lock-2-postmortem](https://falsify.dev/notes/lock-2-postmortem/). Designed for ML eval rigor. Maps to EU AI Act Article 12 evidence as a side effect.

> **Pre-registration + CI for AI-agent claims.** Lock the claim and threshold with SHA-256 *before* running the experiment — or the result doesn't count.

![CI](https://github.com/studio-11-co/falsify/actions/workflows/falsify.yml/badge.svg)
![Multi-lang Conformance](https://github.com/studio-11-co/falsify/actions/workflows/multi-lang-conformance.yml/badge.svg)
![PyPI](https://img.shields.io/pypi/v/falsify?color=brightgreen&label=pypi)
![coverage](https://img.shields.io/badge/tests-598%20passing-brightgreen)
![impls](https://img.shields.io/badge/reference%20impls-4%20(py%20%C2%B7%20js%20%C2%B7%20go%20%C2%B7%20rs)-brightgreen)
![honesty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/studio-11-co/falsify/main/.falsify/badge.json)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-MIT-blue.svg)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13539/badge)](https://www.bestpractices.dev/projects/13539)
[![SchemaStore](https://img.shields.io/badge/schema-in%20SchemaStore-blue.svg)](https://github.com/SchemaStore/schemastore/pull/5673)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.20177839-blue.svg)](https://doi.org/10.5281/zenodo.20177839)
[![UK AISI Inspect](https://img.shields.io/badge/listed-UK%20AISI%20Inspect%20extensions-2ea44f.svg)](https://github.com/UKGovernmentBEIS/inspect_ai/pull/4440)

> Code: MIT. "FALSIFY" name and chevron logo: ™ reserved. See [NOTICE](NOTICE) · [docs/COMMERCIAL.md](docs/COMMERCIAL.md).

---

## The problem

Your team claims the model hits **94% accuracy**. You ship it. Three weeks later a customer proves the real number is **71%**.

The claim was never *falsifiable*. Nobody wrote down — cryptographically, before the experiment ran — what "94%" meant, which dataset, which metric, which threshold. So when the number changed, nobody could say whether the claim was wrong, the data drifted, or the metric got silently relaxed.

This is measurable, not anecdotal. Across the 29 case studies published through Singapore's Global AI Assurance Sandbox — a government programme that asks participants in writing to publish their interpretation thresholds — a reader can recover the rule separating a good result from a bad one in three ([per-document ledger](https://falsify.dev/notes/threshold-disclosure/), so any classification in it can be disputed). Independently, a June 2026 reporting framework for AI evaluations measured the population rate of its own pre-registration field at zero across 635 benchmarks. If you are the one **asking** for this evidence rather than producing it, the gate and a procurement clause are at [falsify.dev/require](https://falsify.dev/require/), together with the four bodies that already require criteria to be fixed before results are known.

**This isn't what MLflow, Docker, or Model Cards do.** MLflow tracks what happened during a run. Docker and DVC let you re-run. Model Cards and Datasheets describe a model after it ships. All three are *post-hoc* — written after the result is known. PRML is *pre-hoc*: the claim is committed before the result is observable. After the fact every other tool still lets you quietly adjust the story; PRML changes the hash and breaks the audit trail the moment you try.

PRML does not prove an ML result is true. It proves that a specific evaluation claim was committed before it could be silently rewritten. That is a smaller guarantee than reproducibility — and a different one.

**Falsify fixes this with a single idea from science:** you must pre-register the claim *before* you run the experiment — the `falsify lock` → `falsify verify` flow shown at the top. If you change the spec after seeing the data, the hash changes, the audit trail breaks, and CI fails with exit code 3.

Deterministic exit codes are the API. CI gates on them. Humans read the audit trail. The claim either survives contact with the data or it doesn't.

---

## 60-second demo

[![60-second walkthrough — paste YAML, lock, get SHA-256, drop badge](https://spec.falsify.dev/demo/demo.gif)](https://spec.falsify.dev/demo/)

*Click for the live looping version, or watch the [MP4](https://spec.falsify.dev/demo/demo.mp4). Full storyboard in [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md).*

[**▶ Watch the longer 90-second walkthrough on YouTube**](https://youtu.be/vVZTNeak5PA) (lock, run, tamper, CI block).

---

## Why this matters

Every week another paper, blog post, or product launch claims an AI metric that quietly evaporates under scrutiny. It's not usually malice — it's that the claim was never structured to be falsifiable. Falsify is the smallest possible tool that forces that structure.

- **ML teams** — gate deploys on pre-registered accuracy / NDCG / recall
- **DevOps** — treat p95 latency claims the same way you treat tests
- **LLM pipelines** — pin prompt + eval + threshold so "it works" means something
- **Research** — replicate a paper by running its spec.lock.json

See [docs/CASE_STUDIES.md](docs/CASE_STUDIES.md) for three concrete adoption stories.

---

## Integrations & ways in

**Open `*.prml.yaml` in your IDE:** as of May 2026 the PRML JSON Schema is in the [SchemaStore](https://github.com/SchemaStore/schemastore/pull/5673) catalog. VS Code, JetBrains IDEs, Helix, Zed, and anything using `yaml-language-server` autocomplete and validate manifest files out of the box. No config.

**Try it without installing:** [`registry.falsify.dev`](https://registry.falsify.dev) — paste a PRML manifest, get a SHA-256 permalink and a README badge. No account, no server-side state beyond the hash.

**Add it to your CI in five lines:** [`studio-11-co/prml-verify-action@v2`](https://github.com/studio-11-co/prml-verify-action) — composite GitHub Action wrapping the falsify CLI ([listed on the GitHub Marketplace](https://github.com/marketplace/actions/prml-verify)). Block merges on tampered or regressed eval claims. Optional public registry receipt (a convenience index, not a cryptographic timestamping authority — see [spec §2.3.4](https://spec.falsify.dev/v0.1#created-at)).

**Already on MLflow?** [`pip install mlflow-falsify`](https://pypi.org/project/mlflow-falsify/) — discoverable plugin that tags every MLflow run with the PRML manifest hash, version, metric, comparator, threshold, and dataset id. Zero code changes to your existing MLflow workflow. Source: [`studio-11-co/mlflow-falsify`](https://github.com/studio-11-co/mlflow-falsify).

**Already running an eval harness?** There is a runnable bridge for ten of them, each using that harness's own scoring machinery rather than a mock, each locking the bar to a SHA-256 before the run and checking the result against it afterwards — PASS, FAIL, or TAMPERED when the threshold moved:
[`deepeval`](examples/deepeval/) ·
[`lm-eval-harness`](examples/lm-eval-harness/) ·
[`promptfoo`](examples/promptfoo/) ·
[`opik`](examples/opik/) ·
[`langfuse`](examples/langfuse/) ·
[`laminar`](examples/laminar/) ·
[`mastra`](examples/mastra/) ·
[`hud`](examples/hud/) ·
[`braintrust`](examples/braintrust/) ·
[`lighteval`](examples/lighteval/).
Each README states exactly what is real and what is not: the Langfuse and Laminar demos stop at the boundary where results would leave the process, because both need a backend; the rest run end to end offline, no key required. All ten are examples, not packages — copy the twenty lines you need.

**Need it locked for one of your published claims?** [`falsify.dev/sprint`](https://falsify.dev/sprint) — Diagnostic Sprint, fixed-scope engagement for regulated AI teams. PRML manifest authored, verifier deployed in CI, audit report shipped. Pricing scoped per client; single-claim review available as a sub-procurement option. Commercial engagements are contracted through Falsify OÜ (reg. 17574308, Tallinn, Estonia).

**Embedding PRML in your platform?** [`docs/EMBED.md`](docs/EMBED.md) — three pure functions (`validate_manifest` / `manifest_hash` / `evaluate_predicate`), a 5-line lock-before-run hook, and an in-toto / ITE-6 attestation bridge (`falsify attest` / `to_intoto_statement`). No CLI required.

**What is PRML?** [`falsify.dev/what-is-prml`](https://falsify.dev/what-is-prml) — plain-English answer page.

---

**Current version:** falsify 0.3.14 (PRML CLI) · falsify-engine 0.3.14 — `falsify --version`.
**Working with Claude Code?** See [CLAUDE.md](CLAUDE.md).

---

## Specification artifacts

This repository is the home of **PRML v0.1** — Pre-Registered ML Manifest Specification. The spec, conformance suite, reference implementations (`impl/`, JS/Go/Rust + a Python reference target), and adjacent documents live under `spec/`:

- **[`spec/PRML-v0.1.md`](spec/PRML-v0.1.md)** — the spec (RFC-style, CC BY 4.0)
- **[`spec/test-vectors/`](spec/test-vectors/)** — 13 v0.1 normative conformance vectors with locked SHA-256 digests, plus 8 v0.2 vectors and 20 reject vectors (the CI matrix: 21 positive, plus 20 negative for Python and JS and 16 for Go and Rust, which read JSON only)
- **[`spec/analysis/positioning-v0.1.md`](spec/analysis/positioning-v0.1.md)** — PRML vs in-toto / SLSA / Model Cards / HELM / ClinicalTrials.gov
- **[`spec/analysis/canonicalization-portability-v0.1.md`](spec/analysis/canonicalization-portability-v0.1.md)** — three cross-language findings from the JS second implementation
- **[`spec/compliance/AI-Act-mapping-v0.1.md`](spec/compliance/AI-Act-mapping-v0.1.md)** — EU AI Act Article 12/17/18/50/72/73 mapping
- **[`spec/compliance/landing.md`](spec/compliance/landing.md)** — compliance-audience landing copy
- **[`spec/paper/`](spec/paper/)** — 14-page arXiv preprint (LaTeX, CC BY 4.0)
- **[`spec/v0.2/ROADMAP.md`](spec/v0.2/ROADMAP.md)** — v0.2 RFC roadmap (freeze 2026-05-22)

**Audit & compliance crosswalks** (subcategory-by-subcategory maps from major AI governance frameworks to PRML fields, FULL/PARTIAL/NONE tagged):

- **[EU AI Act Article 12](https://spec.falsify.dev/eu-ai-act/article-12/)** — code-level pattern for the 2 December 2027 high-risk applicability deadline
- **[Article 12 readiness diagnostic](https://spec.falsify.dev/article-12-readiness/)** — 10-question browser-only self-assessment
- **[NIST AI RMF 1.0 crosswalk](https://spec.falsify.dev/nist-ai-rmf/)** — GOVERN / MAP / MEASURE / MANAGE subcategory map (incl. AI 600-1 GenAI Profile)
- **[ISO/IEC 42001:2023 crosswalk](https://spec.falsify.dev/iso-42001/)** — AIMS clause-by-clause evidence map (Clauses 7-9 + Annex A controls)

**Long-form working notes** (2026-05-23, written for compliance leads, AI governance officers, and notified body assessors preparing for the 2 December 2027 deadline; CC BY 4.0):

- **[EU AI Act readiness assessment](https://falsify.dev/eu-ai-act-readiness/)** — six binding articles, ten-question gap check, evidence shape per obligation
- **[2 August 2026 deadline](https://falsify.dev/ai-act-deadline-august-2026/)** — three application dates, Article 99 penalty structure, ten-week plan
- **[Article 12 logging checklist](https://falsify.dev/article-12-checklist/)** — ten closeable questions, six event categories, printable single-page summary
- **[Notified body evidence](https://falsify.dev/notified-body-evidence/)** — Annex VI vs Annex VII conformity assessment, six artefact families
- **[ISO/IEC 42001 readiness](https://falsify.dev/iso-42001-readiness/)** — seven clauses, EU AI Act Article 17 overlap, twelve-month certification path
- **[Lock #2 post-mortem](https://falsify.dev/notes/lock-2-postmortem/)** — field report on running a falsifiable spec in public

**Reference implementations** (four languages, 13 v0.1 + 8 v0.2 candidate vectors = 21 total; multi-lang CI runs all 21 byte-for-byte per push and daily at 04:00 UTC):

- **Python:** [`falsify.py`](falsify.py) — original reference, uses PyYAML
- **Node.js:** [`impl/js/`](impl/js/) — second reference, ~400 LOC, hand-rolled, zero deps
- **Go:** [`impl/go/`](impl/go/) — third reference, ~450 LOC, hand-rolled, stdlib only
- **Rust:** [`impl/rust/`](impl/rust/) — fourth reference, ~600 LOC, hand-rolled, two deps (`serde_json`, `sha2`)

Hosted spec at [spec.falsify.dev/v0.1](https://spec.falsify.dev/v0.1). Public review thread at [GitHub Discussion #6](https://github.com/studio-11-co/falsify/discussions/6). Comments via `hello@falsify.dev`.

**Companion projects** (separate repos under `studio-11-co`, each MIT or CC0 licensed):

- **[`falsify-cookbook`](https://github.com/studio-11-co/falsify-cookbook)** — field manual for the spec: 13 patterns + 4 anti-patterns, every one a single page with a runnable example, including [Pattern 11: PRML + Sigstore for execution integrity](https://github.com/studio-11-co/falsify-cookbook/blob/main/patterns/11-sigstore-execution.md) closing the §8.1 gap. CC0.
- **[`falsify-integrity-index`](https://github.com/studio-11-co/falsify-integrity-index)** — public scorecard of how 25+ well-known ML eval claims meet the 9 PRML falsifiability criteria. Live at [falsify.dev/integrity](https://falsify.dev/integrity). CC0 data, MIT tooling.
- **[`falsify-inspect`](https://github.com/studio-11-co/falsify-inspect)** — Inspect AI adapter: anchor an Inspect AI eval claim's threshold to a SHA-256 hash before the run, verify the post-run log against it. MIT.
- **[`prml-verify-action`](https://github.com/studio-11-co/prml-verify-action)** — composite GitHub Action ([listed on Marketplace](https://github.com/marketplace/actions/prml-verify)) for CI integration. MIT.
- **[`mlflow-falsify`](https://github.com/studio-11-co/mlflow-falsify)** — MLflow plugin (`pip install mlflow-falsify`) auto-tags every run with the PRML manifest hash. MIT.
- **[`falsify-js`](https://github.com/studio-11-co/falsify-js)** — separately published npm copy of the JS reference implementation (`impl/js` in this repo), kept in sync, byte-identity verified by a CI drift-diff in the falsify-js repo. [`npm install falsify-js`](https://www.npmjs.com/package/falsify-js). MIT.

**Listed in / referenced by** (independent curation — discoverability and third-party review, not adoption claims):

- **[SchemaStore](https://github.com/SchemaStore/schemastore/pull/5673)** — the PRML JSON Schema is in the catalog; `.prml.yaml` autocompletes and validates in VS Code, JetBrains, Cursor, Zed, and anything using `yaml-language-server`. *(real tooling integration)*
- **[theopenlane/awesome-compliance](https://github.com/theopenlane/awesome-compliance)** — Compliance Specs (PR reviewed + merged by an Openlane co-founder)
- **[AthenaCore/AwesomeResponsibleAI](https://github.com/AthenaCore/AwesomeResponsibleAI)** — Responsible-AI Audit section
- **[GenAI-Gurus/awesome-eu-ai-act](https://github.com/GenAI-Gurus/awesome-eu-ai-act)** — EU AI Act Reference Implementations
- **[leipzig/awesome-reproducible-research](https://github.com/leipzig/awesome-reproducible-research)** — Scientific Data Management
- **[ASSERT-KTH/awesome-open-science-software](https://github.com/ASSERT-KTH/awesome-open-science-software)** — Tools (KTH research group)

---

## Beyond the core: the workflow engine

`falsify lock` / `falsify verify` (shown at the top) is the whole PRML core — that is all most teams need. For a managed claim *workflow*, the bundled **`falsify-engine`** CLI adds `init` / `run` / `verdict` / `guard` / `trend` (and more), a `commit-msg` guard that blocks commits contradicting a locked verdict, and optional Claude Code tooling. Full walkthrough: **[docs/ENGINE-TUTORIAL.md](docs/ENGINE-TUTORIAL.md)**.

## Install

```bash
pip install falsify
```

That's it. The `falsify` command is on your `PATH`, the docs site
is at <https://falsify.dev>, and the project page is at
<https://pypi.org/project/falsify>.

Requires Python **3.11+**.

> **Two commands, one install.** `falsify` is the **PRML manifest CLI** — `lock` / `verify` / `hash` / `init` / `test-vectors` on a `*.prml.yaml` manifest (shown at the top). `falsify-engine` is the separate **pre-registration workflow engine** — the `init` → `lock` → `run` → `verdict` / `guard` loop over `.falsify/<name>/` specs. The workflow sections further down use `falsify-engine`; substitute it for `falsify` there. No install needed to verify a manifest: paste it at [registry.falsify.dev](https://registry.falsify.dev).

### Development install (from the repo)

```bash
git clone https://github.com/studio-11-co/falsify
cd falsify
pip install -e .
```

The `-e` editable form is for hacking on falsify itself — your
edits to `falsify.py` take effect immediately without reinstalling.

### Docker

```bash
docker build -t falsify-demo . && docker run --rm -it falsify-demo
```

Runs the auto-demo in a clean container. See
[docs/DOCKER.md](docs/DOCKER.md) for interactive and repo-mount
modes.

### pre-commit integration

Consume falsify's hooks from your own repo:

```yaml
repos:
  - repo: https://github.com/studio-11-co/falsify
    rev: v0.1.4
    hooks:
      - id: falsify-guard
      - id: falsify-doctor
```

Then `pre-commit install && pre-commit install --hook-type commit-msg`.
See [docs/PRE_COMMIT.md](docs/PRE_COMMIT.md) for the full list of
exported hooks and how this repo eats its own dog food.

## Quickstart

```bash
# The falsify PRML CLI — lock a manifest, run your eval, verify.
falsify init accuracy.prml.yaml          # writes a skeleton manifest
# edit accuracy.prml.yaml: metric, comparator, threshold, dataset.hash, seed, producer
falsify lock accuracy.prml.yaml          # canonicalize + SHA-256 + write sidecar
# ... run your eval, get the observed value ...
falsify verify accuracy.prml.yaml --observed 0.934
# PASS (exit 0) · FAIL below threshold (exit 10) · TAMPERED if the spec changed (exit 3)
```

The pre-registration **workflow engine** (claim/falsification specs, `init` → `lock` → `run` → `verdict` → `guard` over `.falsify/<name>/`) ships in the same install as the `falsify-engine` command:

```bash
./demo.sh                                # auto-narrated engine demo (PASS → tamper → FAIL → guard)
falsify-engine init my_claim
# edit .falsify/my_claim/spec.yaml to fill in the template
falsify-engine lock my_claim
falsify-engine run my_claim
falsify-engine verdict my_claim
falsify-engine hook install      # enable the commit-msg guard
```

Exit code `0` on PASS, `10` on FAIL. Everything else is documented
below.

New to pre-registration? Walk through [TUTORIAL.md](TUTORIAL.md) — 10 minutes, zero to first locked claim (core PRML path).

### Start from a template

The five templates are a feature of the **workflow engine** (`falsify-engine`):

```bash
falsify-engine init --template accuracy   # scaffold a ready spec + metric + dataset
falsify-engine lock accuracy
falsify-engine run accuracy
falsify-engine verdict accuracy
```

Five templates ship with a runnable spec + metric + dataset:

- `accuracy` — classifier holdout accuracy ≥ 0.80
- `latency` — p95 request latency ≤ 200 ms
- `brier` — probabilistic calibration Brier ≤ 0.25
- `llm-judge` — LLM-judge agreement rate ≥ 0.75
- `ab` — A/B test absolute lift ≥ 0.05

Each scaffolds into `claims/<name>/` (sources) and mirrors
`spec.yaml` into `.falsify/<name>/` so the CLI runtime works
without further setup. Override the default name with `--name`
or the directory with `--dir`.

### Developer commands

```bash
make install   # pip install pyyaml
make test      # run unittest suite
make smoke     # run tests/smoke_test.sh
make demo      # calibration end-to-end (lock → run → verdict)
```

See [Makefile](Makefile) for all targets (`make help`).

Questions and objections? See [docs/FAQ.md](docs/FAQ.md) — 15
direct answers to "why not just X?" questions.

Feature matrix vs adjacent tools: [docs/COMPARISON.md](docs/COMPARISON.md).

### Explain any claim

`falsify-engine why <name>` is the human-friendly companion to `verdict`
— it always exits `0` and tells you exactly what the next honest
move is:

```
claim: calibration
state: STALE
reasoning: the spec has been edited (sha256:1038219d75a8) but no run
  exists against this hash. Last run was against sha256:164f619d4860.
locked: yes (sha256:164f619d4860, 2h ago)
last run: 2026-04-22T02:10:17+00:00 (2h ago)
next action: `falsify-engine run <name>` to produce a fresh verdict against
  the current spec.
```

Add `--json` for a scripted pipeline, `--verbose` for full hashes
and the last five runs.

### Spot drift with a sparkline

`falsify-engine trend <name>` draws an ASCII sparkline of the metric
across its recorded runs, marks the threshold line, and classifies
the trajectory as **improving**, **degrading**, **flat**, or
**mixed**.

```
claim: calibration
threshold: 0.25 (direction: below)
runs: 20 shown (of 20)

▁▂▂▃▃▄▄▅▅▆▆▆▇▇████
                    TT
threshold=0.25 (shown)

first: 0.12 @ ... (PASS)
last:  0.23 @ ... (PASS)
min:   0.09
max:   0.23
mean:  0.17
latest verdict: PASS
trend: degrading
```

`--ascii` swaps in `_.oO#`; `--width` resizes the sparkline;
`--last` caps history (default 20, max 200).

### Measure the CLI itself

`falsify-engine bench` spawns each subcommand under a fresh temporary
directory and records per-command latency (min / median / p95 /
max / mean / stddev). Useful as a sanity check before a release
or when investigating a suspected startup-time regression.

```bash
falsify-engine bench --runs 5 --commands "--help,list,stats,score"
falsify-engine bench --runs 5 --json     # machine-readable output
```

`--runs <N>` sets the timed-iteration count (default 5, capped at
100); `--warmup <N>` discards the first N spawns so JIT / import
caches stabilize before timing (default 1).

## Exit codes

| Code | Meaning                                       |
|------|-----------------------------------------------|
| 0    | PASS                                          |
| 10   | FAIL                                          |
| 2    | Bad spec / INCONCLUSIVE                       |
| 3    | Hash mismatch (spec tampered)                 |
| 11   | Guard violation (commit blocked)              |

## Claude Code tooling

The repo ships Claude Code **skills** (`hypothesis-author`, `claim-audit`,
`claim-review`, `falsify-ci-doctor`, and the `falsify` orchestrator), two
forked-context **subagents** (`claim-auditor`, `verdict-refresher`), and
**slash commands** (`/new-claim`, `/audit-claims`, `/ship-verdict`) that draft
falsifiable specs and audit text / PR diffs against the verdict log. See
[CLAUDE.md](CLAUDE.md) and the `.claude/` directory.

## Demo

- Walk through the pipeline in 5 runnable steps: [DEMO.md](DEMO.md).
- Second-by-second shooting script for the 3-minute video:
  [docs/DEMO_SHOT_LIST.md](docs/DEMO_SHOT_LIST.md).
- Four more claim types (accuracy regression, latency gate,
  prediction calibration, LLM agreement, AB test):
  [docs/EXAMPLES.md](docs/EXAMPLES.md).

## MCP integration

Expose the verdict store to Claude Desktop / Claude Code via
Model Context Protocol with four read-only tools (`list_verdicts`,
`get_verdict`, `get_stats`, `check_claim`) and three resource URIs.

```bash
pip install -e '.[mcp]'
python -m mcp_server   # speaks MCP over stdio
```

Then merge the snippet in
[`mcp_server/claude_desktop_config.example.json`](mcp_server/claude_desktop_config.example.json)
into your Claude Desktop config, pointing `cwd` at your local
clone. Every Claude session in your org can now query live
verdicts — no more *"I think the latency claim still passes"*;
Claude just asks the MCP server. Falsify itself runs without the
SDK; if `mcp` isn't installed, `python -m mcp_server` exits 2 with
a clear install hint. Full surface in
[`mcp_server/README.md`](mcp_server/README.md).

### Managed Agents (optional)

Deploy the two subagents (`verdict-refresher`, `claim-auditor`)
to Anthropic Console for scheduled and on-demand execution.
See [docs/MANAGED_AGENTS.md](docs/MANAGED_AGENTS.md) for the
setup recipe and manifests under
[`managed_agents/`](managed_agents/).

## Install the git hook

```bash
cp hooks/commit-msg .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

Or, as a symlink so hook updates propagate automatically:

```bash
ln -sf "$(pwd)/hooks/commit-msg" .git/hooks/commit-msg
```

## Repository layout

- `falsify.py` — single-file Python CLI, stdlib + pyyaml only.
- `impl/js/falsify.js` — Node.js second reference implementation (13/13 v0.1 + 8/8 v0.2 = 21/21 vectors). The npm package [`falsify-js`](https://www.npmjs.com/package/falsify-js) is a separately published copy kept in sync with this file; a CI drift-diff in that repo verifies the two files are byte-identical.
- `impl/go/falsify.go` — Go third reference implementation (21/21 vectors).
- `impl/rust/` — Rust fourth reference implementation (21/21 vectors).
- `spec/PRML-v0.1.md` + `spec/test-vectors/v0.1/` (13) + `spec/test-vectors/v0.2/` (8) — spec + conformance suite (21 vectors total).
- `spec/analysis/` — positioning + canonicalization portability findings.
- `spec/compliance/` — EU AI Act mapping + compliance landing copy.
- `spec/paper/` — 14-page arXiv preprint (LaTeX).
- `spec/v0.2/ROADMAP.md` — v0.2 RFC roadmap.
- `hypothesis.schema.yaml` — spec schema (claim, falsification,
  experiment, environment, artifacts).
- `examples/hello_claim/` — tiny smoke-test fixture.
- `examples/calibration_sample/` — anonymized 20-row prediction ledger
  for the Brier score demo.
- `hooks/commit-msg` — the guard hook.
- `tests/` — `unittest` suite plus `smoke_test.sh` end-to-end driver.
- `.claude/skills/` — the five in-session skills.
- `.claude/agents/` — the two forked-context subagents.
- `.claude/commands/` — the three slash commands.
- `.github/workflows/` — CI + PRML manifest verification.

## Self-dogfooding

Falsify uses itself. Three real claims about this codebase live
under `claims/self/`:

- `cli_startup` — CLI startup stays under 500ms median
- `test_coverage_count` — test suite has more than 400 test methods
- `claude_surface` — Claude integration ships more than 8 artifacts

Run `make dogfood` to re-verify. CI runs these on every PR.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

> **Latest — 2026-05-23** · **PRML v0.2 frozen** with all 21 conformance vectors (13 v0.1 stable + 8 v0.2) passing byte-for-byte across the four reference implementations. Lock #2 (public hypothesis on spec's own distribution) resolved at **0/3 external contributors**, mechanism worked, [post-mortem published](https://falsify.dev/notes/lock-2-postmortem/). **`mlflow-falsify` v0.2.0** shipped with `MLFLOW_FALSIFY_TAG_SCOPE=experiment` for HPO sweeps; [MLflow community plugin showcase PR](https://github.com/mlflow/mlflow/pull/23569) is live and under review. Five long-form working notes published for EU AI Act readiness: [readiness assessment](https://falsify.dev/eu-ai-act-readiness/), [2 August 2026 deadline](https://falsify.dev/ai-act-deadline-august-2026/), [Article 12 ten-item checklist](https://falsify.dev/article-12-checklist/), [notified body evidence](https://falsify.dev/notified-body-evidence/), [ISO/IEC 42001 readiness](https://falsify.dev/iso-42001-readiness/). DOI [10.5281/zenodo.20177839](https://doi.org/10.5281/zenodo.20177839). PRML JSON Schema in [SchemaStore](https://github.com/SchemaStore/schemastore/pull/5673) (Mads Kristensen / Microsoft) — `.prml.yaml` files autocomplete in VS Code, JetBrains, Helix, Zed, and Cursor. `registry.falsify.dev` live with README badges at `registry.falsify.dev/badge/<hash>.svg`.

## Roadmap

Two roadmaps run alongside each other:

- **CLI tool roadmap:** [ROADMAP.md](ROADMAP.md) — `falsify` features, integrations, dependencies. **CLI v0.2.0 shipped 2026-05-22.** v0.3 features tracked alongside the v0.3 spec backlog.
- **Specification roadmap:** [spec/v0.2/ROADMAP.md](spec/v0.2/ROADMAP.md) — PRML format evolution, canonicalization grammar, conformance. **Spec v0.2 frozen 2026-05-22.** v0.3 design backlog open under [`spec/v0.3-backlog/`](spec/v0.3-backlog/) (claim trees, suite manifests, selective-disclosure resistance via `leaves_total`).

The CLI is downstream of the spec: spec v0.2 frozen 2026-05-22, CLI v0.2.0 shipped to PyPI the same week. CLI v0.3 is loosely scoped for Q4 2026, tracking the v0.3 spec backlog.

## Trust model

Falsify is a discipline tool, not a zero-trust system. For a full
enumeration of attacks defended and NOT defended, with the exact
exit code or command that catches each, see
[docs/ADVERSARIAL.md](docs/ADVERSARIAL.md). For private disclosure
of invariant breaks, see [.github/SECURITY.md](.github/SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).

See [GOVERNANCE.md](GOVERNANCE.md) for who controls PRML today, the
single-maintainer bus-factor, and why that is a maintenance risk but not a
lock-in risk.
See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards.
See [.github/CODEOWNERS](.github/CODEOWNERS) for module-level
reviewers and [.github/dependabot.yml](.github/dependabot.yml) for
automated dependency updates.
See [docs/GLOSSARY.md](docs/GLOSSARY.md) for definitions of every
term used across the docs.
See [docs/CASE_STUDIES.md](docs/CASE_STUDIES.md) for three concrete
adoption scenarios: ML team, DevOps team, research group.

## Cite

**Cite the spec:** Öztürk, C. (2026). *PRML v0.1*. Zenodo. [https://doi.org/10.5281/zenodo.20177839](https://doi.org/10.5281/zenodo.20177839)
