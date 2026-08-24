# Architecture — Falsification Engine

> **Git for AI honesty.** Lock the claim before the data — or it
> didn't happen.

## One-sentence summary

A deterministic, hash-anchored claim verifier that turns
pre-registration into a CI gate.

## Data flow

    spec.yaml  ──► canonicalize ──► SHA-256 hash ──► spec.lock.json
                                                         │
                                                         ▼
    run command ──► stdout/stderr ──► metric_fn ──► (value, n)
                                                         │
                                                         ▼
              threshold + direction + n ──► verdict.json
                                                         │
            ┌─────────────────────────────────────────────┤
            ▼                                             ▼
    falsify guard (commit-msg)              falsify stats (dashboard)

Every intermediate artifact is a plain text file under
`.falsify/<name>/`. Nothing leaves the directory; every run is
reproducible from what's on disk.

## Core invariants

For the adversarial reasoning behind each invariant below — which
attack class it prevents, which exit code surfaces a violation —
see [ADVERSARIAL.md](ADVERSARIAL.md).

- **Canonical YAML + SHA-256** → the same logical spec always hashes
  to the same 64 hex characters across machines and OSes.
- **The verdict is a pure function** of `(spec.lock.json, run
  artifacts)` — given the same lock and the same run directory,
  `falsify verdict` returns the same PASS/FAIL and writes byte-
  identical `verdict.json` (modulo the `checked_at` timestamp).
- **The commit-msg guard reads `verdict.json`, never recomputes.**
  Guard decisions are therefore as fresh as the last `run + verdict`
  pair, and no faster — stale verdicts stay stale until a human or
  the `verdict-refresher` subagent re-runs them.
- **Exit codes are the API.** `0` PASS, `10` FAIL, `2`
  INCONCLUSIVE / bad spec, `3` hash mismatch, `11` guard violation.
  Everything else the CLI prints is for humans.
- **Replayability.** Every recorded run can be re-executed
  deterministically via `falsify replay <run-id>`; divergence
  between the stored metric value and the re-computed value is a
  failure mode (exit 10), not a soft warning.
- **Direction comparisons are strict.** `direction: above` means
  `observed > threshold` (strictly greater), not `>=`. `direction:
  below` means `observed < threshold`, not `<=`. `direction:
  equals` matches within `1e-9`. A claim phrased "at least N" over
  integer values must set `threshold: N-1` with `direction: above`
  so that the exact value `N` passes the strict inequality — a
  common pitfall is writing `threshold: N` and discovering the
  boundary itself FAILs.

## Module layout

| Module                    | Responsibility                                                         |
|---------------------------|------------------------------------------------------------------------|
| `falsify.py::cmd_init`    | scaffold `.falsify/<name>/` from `examples/template.yaml`              |
| `falsify.py::cmd_lock`    | canonicalize `spec.yaml` → write `spec.lock.json` + SHA-256 hash       |
| `falsify.py::cmd_run`     | subprocess the experiment, capture stdout/stderr + metadata artifact   |
| `falsify.py::cmd_verdict` | import `metric_fn`, apply threshold + direction, write `verdict.json`  |
| `falsify.py::cmd_guard`   | 3-mode: text-match, scan, wrap — exit 11 on contradiction              |
| `falsify.py::cmd_stats`   | aggregate `.falsify/*/verdict.json` into a table or JSON               |
| `falsify.py::cmd_diff`    | unified diff between the locked canonical YAML and the current spec    |
| `falsify.py::cmd_list`    | enumerate spec states with lock hash + last run + verdict              |
| `falsify.py::cmd_hook`    | install / uninstall commit-msg guard with backup                       |
| `falsify.py::cmd_doctor`  | environment + repo + per-spec health check                             |
| `falsify.py::cmd_version` | print version string (also as top-level `--version` flag)              |
| `falsify.py::cmd_export`  | write verdict history as JSONL (audit trail, read-only)                |
| `falsify.py::cmd_verify`  | audit a JSONL export for chain integrity and ordering                  |
| `falsify.py::cmd_replay`  | re-run a stored run's metric and verify the value matches              |
| `falsify.py::cmd_score`   | aggregate honesty score with text / json / shields / svg outputs       |
| `falsify.py::cmd_why`     | human-readable state diagnostic + next honest action (always exit 0)   |
| `falsify.py::cmd_trend`   | ASCII sparkline of the metric across runs with drift classifier        |
| `falsify.py::cmd_bench`   | micro-benchmark per-subcommand latency (min/median/p95/max/mean/stddev) |

## Why SHA-256 of canonical YAML (not of the raw file)

Raw YAML is whitespace-sensitive. Two semantically identical specs
— same keys, same values, different indentation or key order or
comment layout — would hash to different digests, and the lock
would flag trivial editor reformatting as tampering.

`yaml.safe_dump(..., sort_keys=True, default_flow_style=False)`
produces a stable canonical serialization: keys sorted, whitespace
normalized, comments stripped. Any semantic change (threshold,
metric, direction, stopping rule) flips the hash; comment-only
edits and reformatting don't. That's the behavior you want from a
pre-registration primitive — strict on substance, forgiving on
style.

## Why exit codes, not JSON-only output

Unix already has a composition story for yes/no verdicts: exit
codes. They slot into git hooks (`exec falsify guard "$MSG"`), CI
workflows (`run: python3 falsify.py verdict foo`), `make` targets,
and shell `&&` chains without any parsing. The shape of every
integration — "if the claim failed, stop the build" — becomes a
one-liner. JSON output is available where it helps (`list --json`,
`stats --json`, `verdict.json`) but it's a bonus, not the primary
interface. You can use this tool from a `sh` script that never
imports a YAML parser.

## Why forked context for subagents

Both subagents (`claim-auditor` and `verdict-refresher`) load the
full verdict store plus their input text or target spec set. That's
potentially tens of kilobytes of structured context per invocation.
Running them in a forked context means they don't pollute the
parent Claude Code session: the parent's token budget stays clean,
prior reasoning stays intact, and the subagent returns only a
structured report. Opus 4.7's 1M-token window lets each subagent
reason over the entire repo and verdict history as a single unit
without paging.

## Extension points

- **Shipped in 0.1.0 (optional install):** MCP server exposing
  the verdict store. Four tools (`list_verdicts`, `get_verdict`,
  `get_stats`, `check_claim`) and three resource URIs
  (`falsify://verdicts`, `falsify://verdicts/<claim>`,
  `falsify://stats`) wired through the real `mcp.server.Server`
  SDK with decorator-style handlers. The SDK import is lazy —
  module loads without `mcp` so the plain tool functions remain
  importable for unit tests; only `main()` exits 2 when the SDK is
  absent. Install with `pip install -e '.[mcp]'`. Run via
  `python -m mcp_server`. See [`mcp_server/`](../mcp_server/).
- **Shipped in 0.1.0 (manifests) / active in 0.2.0:** Managed
  Agents deployment for `verdict-refresher` (scheduled) and
  `claim-auditor` (on-demand). Manifests live in
  [`managed_agents/`](../managed_agents/); Console setup guide in
  [`docs/MANAGED_AGENTS.md`](MANAGED_AGENTS.md).
- **Claude integration surface (0.1.0).** Five surfaces compose
  the full Claude footprint: **5 skills**
  (`hypothesis-author` drafts specs through a five-question dialogue;
  the `falsify` orchestrator routes any empirical claim to the
  right pipeline step; `claim-audit` runs a fast regex pass over
  arbitrary text; `claim-review` reads a PR diff for unlocked
  specs or silent threshold edits; `falsify-ci-doctor` triages
  red `release-check` runs to an exact fix command), **2
  forked-context subagents**
  (`claim-auditor` for nightly semantic cross-reference;
  `verdict-refresher` for autonomous re-runs of STALE specs),
  **3 slash commands** (`/new-claim` guided scaffold→lock→run;
  `/audit-claims` repo-wide audit report; `/ship-verdict`
  four-gate release check), **1 MCP server** (four read-only
  tools plus three resource URIs over the verdict store), and
  **2 Managed Agents** (scheduled and on-demand deployment
  manifests). Review runs in PR CI; `claim-auditor` runs nightly
  — different failure modes, complementary cadences. See
  [`docs/PR_REVIEW.md`](PR_REVIEW.md).
- **Shipped in 0.1.0:** pre-commit framework integration. The
  [`.pre-commit-hooks.yaml`](../.pre-commit-hooks.yaml) manifest
  exports `falsify-guard`, `falsify-doctor`, and `falsify-stats`
  hooks that any consumer repo can reference; our own
  [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) wires
  them to the local working tree alongside the standard
  pre-commit-hooks hygiene checks. Guide in
  [`docs/PRE_COMMIT.md`](PRE_COMMIT.md).
- Managed Agents cloud deployment for scheduled verdict refresh
  (replaces manually invoking `verdict-refresher`).
- Git `pre-push` hook alongside the existing `commit-msg` hook —
  block a push when any claim is FAIL or STALE, not just commits
  whose messages contradict a verdict.
- Multi-metric specs (e.g. accuracy AND latency) — the current
  schema allows multiple `failure_criteria` entries; verdict logic
  just needs to thread multiple values through `metric_fn`.
- Remote artifact storage (S3 or equivalent) for reproducible
  re-runs of expensive experiments across machines.
- More claim types (see [docs/EXAMPLES.md](EXAMPLES.md) for
  accuracy / latency / calibration / agreement / AB).

The full roadmap lives in [ROADMAP.md](../ROADMAP.md).

## What this is NOT

- **Not a statistical test framework.** We don't compute p-values,
  confidence intervals, or effect sizes. The spec author declares
  the threshold; Falsification Engine just checks observation
  against it deterministically.
- **Not an experiment runner.** We shell out to whatever
  `experiment.command` the spec names. Orchestration, scheduling,
  and resource allocation stay outside scope.
- **Not a replacement for peer review.** It's a tripwire, not a
  court. A PASS verdict says "the claim survived its own
  pre-registered falsification attempt", not "the claim is true".

## Design principles

1. **Determinism over flexibility.** Same inputs → same hash, same
   verdict, same exit code, every time.
2. **Exit codes are the contract.** Anything that breaks the exit
   code table is a breaking change.
3. **Stdlib + one dep (`pyyaml`).** No framework dependencies, no
   test runners beyond `unittest`, no compiled extensions.
4. **Human-readable artifacts.** Specs and verdicts are YAML and
   JSON. Runs are plain stdout/stderr files. No binary blobs.
5. **Every verdict is auditable from a single
   `.falsify/<name>/` directory.** A future reviewer with just that
   directory and the CLI can reproduce the PASS/FAIL decision.
6. **Installable as a package** (`pip install .`) with a `falsify`
   console entry point, not just a script.

## Self-dogfooding

Three locked claims describe falsify's own properties and re-run
on every CI push via the `dogfood` workflow job and the
`make dogfood` target:

| Claim name             | Metric              | Direction | Threshold |
|------------------------|---------------------|-----------|-----------|
| `cli_startup`          | `startup_ms`        | below     | 500       |
| `test_coverage_count`  | `test_count`        | above     | 400       |
| `claude_surface`       | `claude_artifacts`  | above     | 8         |

Source lives at `claims/self/<name>/` (spec + metric + README);
the locked spec is mirrored to `.falsify/<name>/spec.yaml` and
hashed into `spec.lock.json`. The runs directory
(`.falsify/<name>/runs/`) is `.gitignore`d — locks are durable,
runtime artifacts churn. A regression in any of the three gates
the `dogfood` job and must be explained in the PR (adjust the
code, or re-lock with a justified new threshold).

## Release process

- A `v*.*.*` tag push triggers `.github/workflows/release.yml`.
- The workflow runs the full unittest + smoke suite, then verifies
  the tag version matches `falsify.__version__` (exits non-zero on
  mismatch — a mistimed tag bump fails fast).
- On success, it builds sdist + wheel via `python -m build`,
  uploads them as a job artifact, and creates a GitHub Release
  whose body is the matching `CHANGELOG.md [X.Y.Z]` section.
- `concurrency` is set so two rapid tag pushes don't race each
  other; the later one waits.
