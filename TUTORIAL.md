# Tutorial — zero to first locked claim in 10 minutes

This walks the **core PRML path**: lock an evaluation claim's bar before
the run, then verify a result against it — and watch what happens when
someone tries to move the bar afterward. Every command below is real and
runs as written.

> Looking for the older pre-registration **workflow engine** (the
> `init → lock → run → verdict → guard` loop over `.falsify/<name>/`,
> exposed as the `falsify-engine` command)? That's a separate, optional
> tool — see [docs/ENGINE-TUTORIAL.md](docs/ENGINE-TUTORIAL.md).

## Who this is for

You publish or consume ML evaluation claims ("this model is 93% accurate")
and you want them to be **tamper-evident** — checkable, not taken on trust.
You have Python 3.9+ and a terminal.

## What you will build

- An accuracy claim whose bar (metric, threshold, dataset, seed) is locked
  to a SHA-256 **before** the result is known.
- A `PASS` and a `FAIL` verdict against that locked bar.
- A `TAMPERED` verdict — the moved-goalpost case the whole thing exists for.

## Install

    pip install falsify
    falsify --version

## Step 1 — Scaffold a manifest

    falsify init accuracy.prml.yaml

That writes a skeleton with placeholders:

    version: prml/0.1
    claim_id: REPLACE_WITH_UUIDv7
    created_at: "2026-01-01T00:00:00Z"
    metric: accuracy
    comparator: ">="
    threshold: 0.90
    dataset:
      id: your-dataset-id
      hash: REPLACE_WITH_64_LOWERCASE_HEX
    seed: 42
    producer:
      id: your-org-or-domain

## Step 2 — Fill in the bar

Edit `accuracy.prml.yaml` into a real claim. `dataset.hash` is **64
lowercase hex characters** (the SHA-256 of your eval set), no `sha256:`
prefix:

    version: prml/0.1
    claim_id: 01900000-0000-7000-8000-000000000000
    created_at: "2026-06-23T09:00:00Z"
    metric: accuracy
    comparator: ">="
    threshold: 0.90
    dataset:
      id: imagenet-val-2012
      hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    seed: 42
    producer:
      id: acme-ai/model-v2

This says, on the record: *"I will clear accuracy ≥ 0.90 on this exact
dataset."* You are committing to it **before** you have the number.

## Step 3 — Lock it

    falsify lock accuracy.prml.yaml

    locked: accuracy.prml.yaml
      canonical bytes: 297
      sha256:          60318b2380cbf410194e0f1307470e5a32539f6f3a9cffc560040e671483733a
      sidecar:         accuracy.prml.prml.sha256

`lock` canonicalizes the manifest (byte-exact form), takes its SHA-256, and
writes that hash to a sidecar. From here on, any change to a locked field
breaks the hash — and the next `verify` will say so.

## Step 4 — Run your eval, then verify a PASS

Run your real evaluation, get the observed accuracy, and check it against
the locked bar:

    falsify verify accuracy.prml.yaml --observed 0.934
    echo "exit: $?"

    PASS  metric=accuracy  observed=0.934  >=  threshold=0.9
    exit: 0

`0.934 ≥ 0.90`, and the manifest is untouched. Exit `0` = PASS — mechanical,
not rhetorical.

## Step 5 — A FAIL is an honest result

    falsify verify accuracy.prml.yaml --observed 0.82
    echo "exit: $?"

    FAIL  metric=accuracy  observed=0.82  NOT >=  threshold=0.9
    exit: 10

`0.82` misses the bar you locked. That's a true negative — exit `10`. Failing
your own pre-registered bar is exactly the signal PRML is meant to surface.

## Step 6 — The moved goalpost → TAMPERED

Now play the cheater. You scored `0.82`, you don't want a FAIL, so you
quietly lower the bar: change `threshold: 0.90` to `threshold: 0.80` in
`accuracy.prml.yaml`. A naive runtime check would now say "0.82 ≥ 0.80,
passed." PRML doesn't:

    falsify verify accuracy.prml.yaml --observed 0.82
    echo "exit: $?"

    TAMPERED
      recorded:    60318b2380cbf410194e0f1307470e5a32539f6f3a9cffc560040e671483733a
      recomputed:  016ec1a6f2239e85ffae0065d0534b5a351b936448b53ceb51a530dc547b1020
exit: 3

The recomputed hash no longer matches the one locked at Step 3. Exit `3` =
TAMPERED. The bar moved, and it's self-evident from the manifest alone —
anyone can re-check it without trusting you.

## What just happened

- The bar was locked with a hash **before** any result was seen. You could
  not redefine "success" after looking at the number.
- A real miss reads as `FAIL` (exit 10); a moved bar reads as `TAMPERED`
  (exit 3). They are not the same thing, and only the second is cheating.
- Every verdict is an exit code (`0` PASS · `10` FAIL · `3` TAMPERED ·
  `2` bad input · `11` missing sidecar). CI gating is a one-liner.

No account or server is needed to verify — it's a local hash check. You can
also paste any manifest at [registry.falsify.dev](https://registry.falsify.dev)
for a shareable, verifiable permalink.

## Where to go next

- [spec.falsify.dev/v0.1](https://spec.falsify.dev/v0.1) — the PRML v0.1 spec.
- [examples/first-manifest/](examples/first-manifest/) — this same flow as a committed, reproducible example (real dataset, real hashes).
- [docs/ENGINE-TUTORIAL.md](docs/ENGINE-TUTORIAL.md) — the optional
  pre-registration workflow engine (`falsify-engine`).
- [ROADMAP.md](ROADMAP.md) — what ships next.
