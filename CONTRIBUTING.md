# Contributing to Falsification Engine

Thanks for the interest. This project lives or dies by the trust in
its verdicts, so contributions need to keep the determinism contract
intact.

## Contributor licensing

**Two different licences apply, depending on what you are changing.**

- **Specification contributions** — anything under `spec/` — are governed by the
  [Community Specification License 1.0](spec/LICENSE.md), not by the terms
  below. Under that licence you keep your copyright, you grant everyone
  copyright and patent rights within the declared [Scope](spec/Scope.md), and
  you grant nobody a right to sublicense your contribution under different
  terms. Acceptances, withdrawals and patent exclusion notices are recorded in
  [spec/Notices.md](spec/Notices.md).
- **Source-code contributions** — everything else in this repository — are
  governed by the terms in this section.

By submitting a pull request, issue, patch, or any other **source-code**
contribution to this repository, you certify that:

1. You wrote the contribution, or you have the right to submit it
   under the MIT License.
2. Your contribution is licensed to the project under the
   [MIT License](LICENSE).
3. You grant Cüneyt Öztürk (the project author and copyright holder) a
   perpetual, worldwide, non-exclusive, royalty-free, irrevocable
   license to use, reproduce, modify, distribute, and **sublicense**
   your contribution under any terms, including future commercial
   or dual-license arrangements.

This is a standard developer-certificate-of-origin-plus-re-licensing
clause used by projects like Grafana, MongoDB (pre-SSPL), and Sentry.
It keeps the open-source commitment intact (nothing can be removed
from MIT) while allowing the project to sustain itself through
enterprise licensing if that becomes necessary.

See [NOTICE](NOTICE) and [docs/COMMERCIAL.md](docs/COMMERCIAL.md) for
the trademark and commercial-use policy.

Contributors using Claude Code should also read
[CLAUDE.md](CLAUDE.md) — it encodes the repo's prime directive and
development rules.

## Code of conduct

By participating, you agree to uphold the Code of Conduct. See
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Ground rules

- If you've never used falsify before, do [TUTORIAL.md](TUTORIAL.md)
  first — it's the fastest way to internalize the lock-then-run
  contract before you start changing the code.
- Every new feature or bug fix must include unittest coverage.
- Never break the exit-code contract (`0` PASS, `10` FAIL, `2`
  bad spec, `3` hash mismatch, `11` guard violation). If you need a
  new code, propose it in an issue first.
- Canonical YAML hashing is the spine — do not change the
  canonicalization rules without an RFC-style issue.
- Stdlib + `pyyaml` only. No new dependencies without discussion.

## Setup

1. Fork and clone.
2. Install the one dependency: `make install` (or
   `pip install -e .` for an editable install that also exposes
   the `falsify` console entry point).
3. Run the full local CI suite: `make ci` (unittest + smoke + calibration
   end-to-end + skill lint).
4. All of those must pass before you open a PR.
5. *(Recommended)* Install pre-commit hooks so style + guard
   checks fire locally on every commit:

       pip install pre-commit
       pre-commit install
       pre-commit install --hook-type commit-msg

   Configuration lives in `.pre-commit-config.yaml`; see also
   [docs/PRE_COMMIT.md](docs/PRE_COMMIT.md).

## Branching and commits

- Branch naming: `feature/<short-slug>` or `fix/<short-slug>`.
- Commit messages: present-tense verb first, subject line under 72
  chars. Explain the *why* in the body.
- If Claude (or any LLM) co-authored the commit, include a
  `Co-Authored-By:` trailer.
- One logical change per commit — easier to revert, easier to review.

## Pull requests

- [ ] Tests added and passing (`python3 -m unittest discover tests -v`)
- [ ] Smoke test passing (`bash tests/smoke_test.sh`)
- [ ] If you changed `falsify.py` semantics, update `DEMO.md` and
      `docs/ARCHITECTURE.md`
- [ ] If you added a CLI flag, update `README.md`
- [ ] No new dependencies beyond `pyyaml` (unless discussed in an
      issue first)

## Adding a new CLI subcommand

1. Add `cmd_<name>(args)` in `falsify.py`.
2. Wire it into the argparse setup alongside the existing
   subcommands.
3. Add `tests/test_<name>.py` using `unittest` +
   `tempfile.TemporaryDirectory` for isolation — every test should
   run in a throwaway `.falsify/` directory.
4. Add a one-liner to the commands list in `README.md`.
5. If the subcommand is juror-demo-relevant, add a mention to
   `DEMO.md`.

## Adding a Claude Code skill or subagent

- Skills live in `.claude/skills/<name>/SKILL.md` with YAML frontmatter
  whose keys are `name`, `description`, `allowed-tools`, `context`.
- Subagents live in `.claude/agents/<name>.md` with YAML frontmatter
  whose keys are `name`, `description`, `tools`, `model`, `context`.
- All skills and subagents must use `context: fork` unless there's
  a justified reason to share parent context.
- Add a `tests/test_skill_<name>.py` or
  `tests/test_agent_<name>.py` that validates the frontmatter parses
  as YAML and contains the required keys.
- The CI workflow's `skill-lint` job will re-validate every
  `SKILL.md` and agent file on push.

## Reporting a bug

Open an issue with:

- The exact `falsify` command that failed.
- Exit code you got.
- Exit code you expected.
- Minimal `spec.yaml` that reproduces it.
- Output of `python3 falsify.py --version` so we know which version
  you were on.

## Security

If you find a way to make `falsify guard` pass on a contradicting
claim — or to make two semantically different specs produce the
same canonical hash — open a **private** security advisory or email
the maintainer directly. Do **not** file a public issue for these;
they break the core guarantee and deserve a coordinated fix.

## Code style

- Python: type hints on public functions, a docstring on anything
  more than 5 lines of body.
- YAML: 2-space indent, lowercase keys, double-quoted strings when
  the value contains punctuation that YAML plain scalars would
  mishandle.
- Markdown: reference-style links where the target is reused, inline
  links when it's one-off.

## Releasing (maintainer notes)

1. Update `__version__` in `falsify.py` to the new version (and
   `version` in `pyproject.toml` to match — `tests/test_pyproject.py`
   enforces this).
2. Update `CHANGELOG.md` — move items from `[Unreleased]` into a
   new `## [X.Y.Z] — YYYY-MM-DD` section with today's date.
3. Before pushing a tag, run:

       make release-check

   Expected output ends with `Ready to tag and push.` If any gate
   FAILs, fix before tagging. WARN gates (typically placeholder
   scans on `<USER>` / `<VIDEO_URL>`, or a dirty working tree)
   require human judgment — read the message and decide whether
   to proceed.
4. Commit the version bump, then tag and push:

       git tag vX.Y.Z
       git push origin main --tags

5. `.github/workflows/release.yml` fires on the tag push. It runs
   the unittest suite + smoke test, verifies the tag matches the
   code's `__version__`, builds sdist + wheel, and creates the
   GitHub Release with the matching CHANGELOG section as the body.
6. Verify the Release page on GitHub once the workflow finishes.
   If the workflow failed, fix forward — delete the tag locally
   and remotely, fix the issue, re-tag, re-push.

## License

By contributing, you agree that your work is released under the
MIT license of this repository.
