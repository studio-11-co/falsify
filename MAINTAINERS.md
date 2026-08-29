# Maintainers

This file lists the people who can merge changes to this repository, and states
what that does and does not guarantee. It is deliberately short and deliberately
honest: see [GOVERNANCE.md](./GOVERNANCE.md) for the fuller picture.

## Current maintainers

| Name | Role | GitHub | Contact | Since |
|---|---|---|---|---|
| Cüneyt Öztürk | Specification editor · reference-implementation maintainer · registry operator | `studio-11-co` | `hello@falsify.dev` | 2026-04 |

Organisation: Falsify OÜ (Estonia, registry code 17574308).

## Bus factor

**One.** There is no second maintainer, no steering committee, and no
independent review board. Every specification change, conformance vector and
release in this repository has been authored and merged by the person named
above.

A team that requires a multi-vendor maintenance guarantee before adopting PRML
does not have one. The mitigations that do exist are structural rather than
organisational, and they are the reason PRML is worth adopting anyway:

- The specification is published under the
  [Community Specification License 1.0](./spec/LICENSE.md), which grants both
  copyright and patent rights to everyone, irrevocably, within the declared
  [Scope](./spec/Scope.md).
- The reference implementations are MIT-licensed, in four languages, and are
  byte-equivalent against a published conformance suite.
- Verification does not depend on this project remaining online: a manifest, its
  digest and an RFC 3161 token can be checked offline by anyone.
- Manifests are plain canonical YAML. Anyone who adopts PRML can leave it
  without a migration.

In other words, if this project stops, the format does not become unreadable and
nobody needs our permission to continue it.

## What a maintainer does

- Reviews and merges changes to the specification, the conformance vectors and
  the reference implementations.
- Decides releases and version numbering, and keeps the four implementations
  byte-equivalent.
- Runs the cross-surface consistency check before any release
  (`scripts/check-consistency.sh`) and fixes every surface it flags.
- Responds to security reports per [SECURITY.md](./SECURITY.md).
- Records licence acceptances, withdrawals and exclusion notices in
  [spec/Notices.md](./spec/Notices.md).

## Becoming a maintainer

There is no quota and no waiting list. The path is ordinary and unglamorous:
land substantive changes, review other people's, and demonstrate the judgement
to say no to a change that would break byte-equivalence or widen a claim beyond
what the evidence supports. A contributor who has done that consistently will be
invited, and this file will be updated in the same pull request.

Contributions to the **specification** are governed by the Community
Specification License 1.0 (see [spec/Notices.md](./spec/Notices.md)).
Contributions to the **source code** are governed by the MIT License and the
contributor terms in [CONTRIBUTING.md](./CONTRIBUTING.md). These are separate;
a specification contribution does not fall under the source-code contributor
terms.

## Succession

If the maintainer becomes unavailable, the licences above already permit anyone
to fork, continue and re-publish the specification and the implementations
without further permission. What does **not** transfer automatically is the
`FALSIFY` name and mark, the `falsify.dev` domains and the public registry —
see [TRADEMARK.md](./TRADEMARK.md). A fork must use a different name, which is
the normal and intended outcome.
