# Docker — reproducible Falsify

A single `Dockerfile` at the repo root produces a clean
`falsify-demo` image. Zero local Python setup; anyone can run the
full demo with two commands.

## Quick run

```bash
docker build -t falsify-demo .
docker run --rm -it falsify-demo
```

The default command runs `./demo.sh` with `DEMO_AUTO=1`. You see
the full PASS → tamper → FAIL → guard-block story in about 15
seconds.

## Interactive session

```bash
docker run --rm -it falsify-demo bash
```

Once inside, any falsify command works:

```bash
falsify stats
falsify stats --html > /tmp/d.html
falsify doctor
```

## Mounting your own repo

If you want to falsify claims in your own codebase, mount it:

```bash
docker run --rm -it -v "$(pwd):/work" -w /work falsify-demo bash
# inside the container:
falsify init my_claim
# edit .falsify/my_claim/spec.yaml, then:
falsify lock my_claim
falsify run my_claim
falsify verdict my_claim
```

## Image size

Approximately 150–180 MB: the `python:3.12-slim` base, `git`
(needed for the commit-msg hook and the build-time `git init`),
`pyyaml`, and the installed `falsify` entry point.

## Build determinism

The image pins the Python base to `3.12-slim` and installs from
`pyproject.toml`. Between two builds on the same day you should
get identical behavior. The image is not bit-reproducible — Docker
base layers and `apt` mirror contents can shift — but it is
*behaviorally* reproducible against the same commit of this repo.

## Publishing

Pending push to Docker Hub or GHCR. Tracked under 0.2.0 in
[ROADMAP.md](../ROADMAP.md).
