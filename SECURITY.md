# Security Policy

## Reporting a vulnerability

Email **hello@falsify.dev** with the subject prefix `[SECURITY]`. Please include
a description, affected component and version, and a reproduction if you have one.
We aim to acknowledge within 3 working days. Do not open a public issue for
suspected vulnerabilities.

## Supported versions

| Component | Supported |
|-----------|-----------|
| `falsify` PRML CLI (PyPI) | latest 0.4.x |
| `falsify-js` (npm) | latest 0.2.x |
| `prml-verify-action` | latest `v2.x` |
| PRML spec | v0.1 (stable), v0.2 (frozen RFC) |

## Trust model — what each tool does with a manifest

PRML manifests are plain data. Treat a manifest you did not write the same way
you would treat any file from an untrusted source.

**Safe on untrusted manifests.** The PRML CLI verbs `falsify lock`,
`falsify verify`, and `falsify hash` (and the `falsify-js` equivalents) only
read, canonicalize, hash, and compare. They never execute anything contained in
a manifest. These are safe to run in CI on a pull request's manifest.

**Not safe on untrusted manifests — by design.** The optional workflow engine
(`falsify-engine run` and `falsify-engine replay`) is a task runner: it executes
the `experiment.command` and imports the `experiment.metric_fn` declared in the
spec. That is the whole point of those commands, exactly like a Makefile or a CI
config. Do **not** run `falsify-engine run`/`replay` against a spec you do not
trust. In CI, only run them against claims that have already been reviewed and
merged — never against spec files taken straight from an incoming pull request.

If you only need the pre-registration / tamper-evidence guarantee, you do not
need the engine at all: `falsify lock` + `falsify verify` is sufficient and is
safe on untrusted input.

## Related surfaces

- **`prml-verify-action`** passes inputs to the CLI via environment variables
  and validates the registry URL; see that repository's own hardening.
- **registry.falsify.dev** accepts unauthenticated manifests, escapes all
  rendered fields, and parses YAML with a safe loader.
