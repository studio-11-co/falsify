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
[![SchemaStore](https://img.shields.io/badge/schema-in%20SchemaStore-blue.svg)](https://github.com/SchemaStore/schemastore/pull/5673)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.20177839-blue.svg)](https://doi.org/10.5281/zenodo.20177839)

> Code: MIT. "FALSIFY" name and chevron logo: ™ reserved. See [NOTICE](NOTICE) · [docs/COMMERCIAL.md](docs/COMMERCIAL.md).

---

**Open `*.prml.yaml` in your IDE:** as of May 2026 the PRML JSON Schema is in the [SchemaStore](https://github.com/SchemaStore/schemastore/pull/5673) catalog. VS Code, JetBrains IDEs, Helix, Zed, and anything using `yaml-language-server` autocomplete and validate manifest files out of the box. No config.

**Try it without installing:** [`registry.falsify.dev`](https://registry.falsify.dev) — paste a PRML manifest, get a SHA-256 permalink and a README badge. No account, no server-side state beyond the hash.

**Add it to your CI in five lines:** [`studio-11-co/prml-verify-action@v2`](https://github.com/studio-11-co/prml-verify-action) — composite GitHub Action wrapping the falsify CLI ([listed on the GitHub Marketplace](https://github.com/marketplace/actions/prml-verify)). Block merges on tampered or regressed eval claims. Optional public registry receipt (a convenience index, not a cryptographic timestamping authority — see [spec §2.3.4](https://spec.falsify.dev/v0.1#created-at)).

**Already on MLflow?** [`pip install mlflow-falsify`](https://pypi.org/project/mlflow-falsify/) — discoverable plugin that tags every MLflow run with the PRML manifest hash, version, metric, comparator, threshold, and dataset id. Zero code changes to your existing MLflow workflow. Source: [`studio-11-co/mlflow-falsify`](https://github.com/studio-11-co/mlflow-falsify).

**Need it locked for one of your published claims?** [`falsify.dev/sprint`](https://falsify.dev/sprint) — Diagnostic Sprint, fixed-scope engagement for regulated AI teams. PRML manifest authored, verifier deployed in CI, audit report shipped. Pricing scoped per client; single-claim review available as a sub-procurement option.

**Embedding PRML in your platform?** [`docs/EMBED.md`](docs/EMBED.md) — three pure functions (`validate_manifest` / `manifest_hash` / `evaluate_predicate`), a 5-line lock-before-run hook, and an in-toto / ITE-6 attestation bridge (`falsify attest` / `to_intoto_statement`). No CLI required.

**What is PRML?** [`falsify.dev/what-is-prml`](https://falsify.dev/what-is-prml) — plain-English answer page.

---

## The problem

Your team claims the model hits **94% accuracy**. You ship it. Three weeks later a customer proves the real number is **71%**.

The claim was never *falsifiable*. Nobody wrote down — cryptographically, before the experiment ran — what "94%" meant, which dataset, which metric, which threshold. So when the number changed, nobody could say whether the claim was wrong, the data drifted, or the metric got silently relaxed.

**This isn't what MLflow, Docker, or Model Cards do.** MLflow tracks what happened during a run. Docker and DVC let you re-run. Model Cards and Datasheets describe a model after it ships. All three are *post-hoc* — written after the result is known. PRML is *pre-hoc*: the claim is committed before the result is observable. After the fact every other tool still lets you quietly adjust the story; PRML changes the hash and breaks the audit trail the moment you try.

PRML does not prove an ML result is true. It proves that a specific evaluation claim was committed before it could be silently rewritten. That is a smaller guarantee than reproducibility — and a different one.

**Falsify fixes this with a single idea from science:** you must pre-register the claim *before* you run the experiment. If you change the spec after seeing the data, the hash changes, the audit trail breaks, and CI fails with exit code 3.

    $ falsify-engine lock accuracy_claim        # SHA-256 the spec
    $ falsify-engine run  accuracy_claim        # reproducible experiment
    $ falsify-engine verdict accuracy_claim     # exit 0 = PASS, 10 = FAIL, 3 = tampered

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

**Current version:** falsify 0.3.9 (PRML CLI) · falsify-engine 0.3.9 — `falsify --version`.
**Working with Claude Code?** See [CLAUDE.md](CLAUDE.md).

---

## Specification artifacts

This repository is the home of **PRML v0.1** — Pre-Registered ML Manifest Specification. The spec, conformance suite, reference implementations (`impl/`, JS/Go/Rust + a Python reference target), and adjacent documents live under `spec/`:

- **[`spec/PRML-v0.1.md`](spec/PRML-v0.1.md)** — the spec (RFC-style, CC BY 4.0)
- **[`spec/test-vectors/v0.1/`](spec/test-vectors/v0.1/)** — 13 conformance vectors with locked SHA-256 digests
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
- **[`falsify-js`](https://github.com/studio-11-co/falsify-js)** — JS reference implementation, [`npm install falsify-js`](https://www.npmjs.com/package/falsify-js). MIT.

**Listed in / referenced by** (independent curation — discoverability and third-party review, not adoption claims):

- **[SchemaStore](https://github.com/SchemaStore/schemastore/pull/5673)** — the PRML JSON Schema is in the catalog; `.prml.yaml` autocompletes and validates in VS Code, JetBrains, Cursor, Zed, and anything using `yaml-language-server`. *(real tooling integration)*
- **[theopenlane/awesome-compliance](https://github.com/theopenlane/awesome-compliance)** — Compliance Specs (PR reviewed + merged by an Openlane co-founder)
- **[AthenaCore/AwesomeResponsibleAI](https://github.com/AthenaCore/AwesomeResponsibleAI)** — Responsible-AI Audit section
- **[GenAI-Gurus/awesome-eu-ai-act](https://github.com/GenAI-Gurus/awesome-eu-ai-act)** — EU AI Act Reference Implementations
- **[leipzig/awesome-reproducible-research](https://github.com/leipzig/awesome-reproducible-research)** — Scientific Data Management
- **[ASSERT-KTH/awesome-open-science-software](https://github.com/ASSERT-KTH/awesome-open-science-software)** — Tools (KTH research group)

---

## Why

AI agents make empirical claims all day — *"accuracy is up"*, *"the
new retriever is faster"*, *"this filter catches every edge case"*.
We rarely pin down the threshold, the metric, or the stopping rule
before the data arrives.

Without pre-registration, every verdict is post-hoc rationalization:
the goalposts move a little, the sample is chosen a little, the
winning explanation is kept.

Falsification Engine forces scientific discipline onto that loop.
You declare the test, lock the spec with a cryptographic hash, run
the experiment, and read the exit code. PASS or FAIL is mechanical,
not rhetorical — and CI enforces it on every push.

## What you get

- The `falsify-engine` CLI with **18 subcommands**: `init`,
  `lock`, `run`, `verdict`, `guard`, `list`, `stats`, `diff`, `hook`,
  `doctor`, `version`, `export`, `verify`, `replay`, `why`, `trend`,
  `score`, `bench`.
- A `commit-msg` git hook that blocks commits whose messages
  contradict a locked verdict.
- A GitHub Actions workflow that re-verdicts every push and PR
  across Python 3.11 and 3.12.
- **Five Claude Code skills** and **two forked-context subagents**
  that draft specs, audit arbitrary text against the verdict log,
  review PR diffs for honesty violations, and keep the log itself
  fresh.

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

## The Opus 4.7 layers

**Skills** (`.claude/skills/`) — in-session helpers that fire on
trigger phrases.
- `hypothesis-author` walks the user through a 5-question dialogue
  and writes a falsifiable `spec.yaml`.
- `falsify` is the orchestrator: routes any empirical claim to the
  right place in the init → lock → run → verdict pipeline.
- `claim-audit` runs a fast keyword+regex audit over pasted text
  and escalates to the `claim-auditor` subagent when paraphrases or
  >2 claims show up.
- `claim-review` reads a PR diff and flags unlocked specs, silent
  threshold edits, and `metric_fn` references to missing modules —
  runs in PR CI, exits `1` on any CRITICAL finding. See
  [`docs/PR_REVIEW.md`](docs/PR_REVIEW.md).
- `falsify-ci-doctor` ingests `make release-check` output and
  maps each FAIL gate to a likely cause and an exact fix command
  — one-shot triage when CI is red.

**Subagents** (`.claude/agents/`) — forked-context agents invoked
via the `Task` tool for heavier work.
- `claim-auditor` does the semantic cross-reference that the
  keyword-pass `claim-audit` skill deliberately skips; used on PR
  bodies, release notes, and README edits.
- `verdict-refresher` scans `.falsify/*/` for STALE, INCONCLUSIVE,
  or UNRUN verdicts and re-runs them through the CLI — keeping
  `guard` decisions trustworthy.

**Slash commands** (`.claude/commands/`) — in-IDE shortcuts that
compose the skills and CLI.
- `/new-claim <template> [name]` — guided scaffold → lock → run →
  verdict for one of the five templates.
- `/audit-claims` — repo-wide semantic audit; merges
  `list`/`stats`/`score` with findings from the `claim-audit`
  skill into a single markdown report.
- `/ship-verdict <name>` — four-gate release check (verdict,
  freshness, replay, audit-chain). Exits non-zero on any gate
  failure. Does not ship; only verifies.

**CI** (`.github/workflows/falsify.yml`) — on every push and PR,
the workflow runs the unittest suite, `tests/smoke_test.sh`, the
calibration end-to-end (`lock` → `run` → `verdict`), a guard self-check,
and a skill-lint pass over every SKILL.md and agent file.

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
- `impl/js/falsify.js` — Node.js second reference implementation (13/13 v0.1 + 8/8 v0.2 = 21/21 vectors). Also published to npm as [`falsify-js`](https://www.npmjs.com/package/falsify-js).
- `impl/go/falsify.go` — Go third reference implementation (21/21 vectors).
- `impl/rust/` — Rust fourth reference implementation (21/21 vectors).
- `spec/PRML-v0.1.md` + `spec/test-vectors/v0.1/` (12) + `spec/test-vectors/v0.2/` (8) — spec + conformance suite.
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

## Built with

Claude Opus 4.7 (1M context), in three days, for the Anthropic
Built with Opus 4.7 hackathon.

**Cite the spec:** Öztürk, C. (2026). *PRML v0.1*. Zenodo. [https://doi.org/10.5281/zenodo.20177839](https://doi.org/10.5281/zenodo.20177839)
