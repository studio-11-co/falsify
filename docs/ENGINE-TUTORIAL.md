# Engine tutorial — the pre-registration workflow (optional)

> This covers the **workflow engine**, exposed as the `falsify-engine`
> command: a `init → lock → run → verdict → guard` loop that runs your
> metric and records verdicts under `.falsify/<name>/`. It is separate
> from the core PRML manifest path (`falsify lock` / `verify`) — for that,
> see [TUTORIAL.md](../TUTORIAL.md). Use the engine when you want falsify
> to execute the eval and keep the run history, not just verify a claim.

## What you will build

- A claim that a string is mostly vowels, locked with a SHA-256 hash.
- A run that falsifies the claim against input `rhythm`.
- A fix that makes the claim pass against input `aeiou`, re-locked
  with a new hash so the history stays honest.

## Prerequisites

- Python 3.11+, git, 15 minutes

Install the package so the `falsify-engine` command is on your PATH:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e .

Check the install:

    falsify-engine --version

## Step 1 — Initialize

From the repo root, scaffold a new claim directory:

    falsify-engine init vowels

This creates `.falsify/vowels/spec.yaml` — a template you will
fill in next. The `.falsify/` directory is where every locked
spec, run artifact, and verdict lives. One subdirectory per claim.

## Step 2 — Write your first claim

> **In a hurry?** Run `falsify-engine init --template accuracy` to get a
> working `claims/accuracy/` (spec + metric + dataset) plus a
> mirrored `.falsify/accuracy/spec.yaml`, and skip ahead to Step 3.
> Five templates ship: `accuracy`, `latency`, `brier`, `llm-judge`,
> `ab`. The walkthrough below builds the same structure by hand so
> you understand what each piece does.

You need two files: a Python metric function and a spec. Put the
metric at `claims/vowels.py`:

    # claims/vowels.py
    from pathlib import Path

    def vowel_ratio(run_dir):
        """Return (ratio, n) where ratio = vowels / characters."""
        text = (Path(run_dir) / "stdout.txt").read_text().strip()
        if not text:
            return (0.0, 0)
        vowels = sum(1 for ch in text.lower() if ch in "aeiou")
        return (vowels / len(text), len(text))

Now replace `.falsify/vowels/spec.yaml` with the real claim:

    claim: "Most characters in the sample are vowels (ratio above 0.5)."
    falsification:
      failure_criteria:
        - metric: vowel_ratio
          direction: above
          threshold: 0.5
      minimum_sample_size: 1
      stopping_rule: "one echo"
    experiment:
      command: "echo rhythm"
      metric_fn: "claims.vowels:vowel_ratio"

No placeholders, no `TODO`, no `<...>` markers — `falsify-engine lock`
will refuse the spec otherwise.

## Step 3 — Lock it

    falsify-engine lock vowels

What happened: the CLI canonicalized your YAML (sorted keys,
stripped comments, normalized whitespace), computed the SHA-256 of
the canonical text, and wrote `.falsify/vowels/spec.lock.json`
with `spec_hash`, `locked_at`, and the canonical YAML itself. From
this moment on, any edit to `spec.yaml` that changes its canonical
form will break the lock and `falsify-engine run` will refuse to proceed
unless you re-lock with `--force`.

## Step 4 — Run and watch it FAIL

    falsify-engine run vowels
    falsify-engine verdict vowels
    echo "exit: $?"

Expected output from `verdict`:

    Verdict: FAIL
      observed vowel_ratio = 0.0
      threshold: above 0.5

    exit: 10

The input `rhythm` has zero vowels, ratio 0.0, which is not above
0.5. Exit code 10 means FAIL — mechanical, not rhetorical.

## Step 5 — Fix the claim honestly

You have two options and both require a fresh lock. That is the
point: the hash is what makes the fix auditable.

Option (a): lower the threshold. Change `threshold: 0.5` to
`threshold: 0.0` in `.falsify/vowels/spec.yaml`. This is a claim
change — the goalpost moved — and anyone reading the lock history
will see it.

Option (b, what this tutorial does): keep the claim, swap the
data. Change the command line to test a string that actually is
mostly vowels:

    experiment:
      command: "echo aeiou"
      metric_fn: "claims.vowels:vowel_ratio"

Either way, re-lock. The hash changes, so `falsify-engine` forces the
decision:

    falsify-engine lock vowels --force

`--force` is the required ceremony. You can never *silently* change
a locked spec; you can only visibly re-lock it.

## Step 6 — PASS

    falsify-engine run vowels
    falsify-engine verdict vowels
    echo "exit: $?"

Expected:

    Verdict: PASS
      observed vowel_ratio = 1.0
      threshold: above 0.5

    exit: 0

`aeiou` is 100% vowels. The claim now holds.

## Step 7 — Inspect

Commands to see what the system knows about your claim:

    falsify-engine list
    falsify-engine stats
    falsify-engine export --output audit.jsonl
    falsify-engine verify audit.jsonl
    falsify-engine replay <run-id>
    falsify-engine why vowels
    falsify-engine trend vowels
    falsify-engine bench   # sanity-check the CLI's own responsiveness

`replay` re-runs the metric against the same dataset and exits 0
only if the value matches bit-for-bit; mismatch or stale spec are
hard errors. `why` is the plain-English companion to `verdict` —
it always exits 0 and tells you what the next honest move is for
any state (PASS, FAIL, INCONCLUSIVE, STALE, UNRUN, UNLOCKED).
`trend` draws an ASCII sparkline of the metric across runs with
an `improving`/`degrading`/`flat`/`mixed` classifier.

`list` gives you a table of every claim and its state. `stats`
aggregates counts. `export` dumps an append-only JSONL audit trail
of every lock and verdict. `verify` walks that JSONL and confirms
the hash chain is intact — a tampered file would exit 10.

## What just happened

- Your claim was locked with a hash **before** any data was seen.
- The canonical hash prevents silent edits. Any change requires a visible
  `--force` re-lock, which produces a new hash that anyone can audit.
- The verdict is an exit code. `0` for PASS, `10` for FAIL, `3` for
  tampering. CI gating is a one-line addition to any workflow.

## Where to go next

- [TUTORIAL.md](../TUTORIAL.md) — the core PRML manifest path (`lock` / `verify`).
- [DEMO.md](../DEMO.md) — the 5-step walkthrough used in the demo video.
- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — design principles and data flow.
- Add a live honesty badge with
  `falsify-engine score --format shields --output .falsify/badge.json`.
