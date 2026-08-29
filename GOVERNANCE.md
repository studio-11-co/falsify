# Governance

This document states, plainly, who controls PRML and the `falsify` reference
implementation today — and what that does and does not guarantee. It exists so
that anyone evaluating PRML for adoption can judge the maintenance risk
honestly, without having to infer it.

## What PRML is, for governance purposes

PRML is a **small primitive**, not a multi-stakeholder standard. The intended
end state is that PRML is **embedded inside a host** — an evaluation platform,
a model registry, an agent marketplace, a governance tool — and travels with
that host, the way a checksum or a signature format does. It is deliberately
*not* positioned as a standalone standards body with a charter, dues, and a
plenary. Where any surface calls PRML a "standard," read it as "an open,
versioned specification anyone may implement," not "a standard ratified by a
recognized standards organization." It has not been ratified, endorsed, or
certified by ISO, CEN/CENELEC, NIST, or any notified body.

## Who decides today

- **Sole editor and maintainer:** Cüneyt Öztürk (`hello@falsify.dev`).
- All specification text, conformance vectors, and crosswalks are currently
  authored and merged by the editor. There is **no** steering committee, no
  technical working group, and no independent review board at this stage.
- This is a genuine **bus-factor of one**. A team that needs a multi-vendor
  governance guarantee before adoption does not have it yet, and should treat
  that as an open risk — or bring it in-house (see "Capture resistance").

## How decisions are made

- **Specification changes** land via pull request and are recorded in
  `CHANGELOG.md`. Breaking changes require a version bump (v0.1 → v0.2 → …) and
  a frozen conformance-vector set; published vectors are never silently
  changed.
- **Errata** to a frozen version are published as dated notes inside the
  affected spec section (see the §8.1 erratum in `spec/PRML-v0.1.md`), never by
  rewriting history.
- **Substantive proposals** are taken in GitHub Discussions / Issues on
  `studio-11-co/falsify`. Anyone may open one; there is no membership gate.

## Capture resistance

Single-maintainer control is a maintenance risk, but it is **not** a lock-in
risk, by construction:

- The specification is published under the **[Community Specification License
  1.0](spec/LICENSE.md)** (since 2026-08-29; previously CC BY 4.0, and copies
  distributed before that date remain available under it). That licence grants
  copyright *and* patent rights, irrevocably, within the declared
  [Scope](spec/Scope.md). The reference implementations are **MIT**. Anyone may
  fork, re-implement, or re-host without permission.
- Conformance is defined by **published byte-level test vectors**, not by a
  blessed binary. A second implementation in any language can prove
  equivalence independently.
- There is no registrar, license server, or hosted dependency required to
  *use* PRML: `SHA-256` + the manifest + the dataset is sufficient.

So if the editor disappears, the artifact does not: the spec, the vectors, and
four implementations remain usable and forkable in perpetuity.

## Succession and transfer

PRML is intended to be **handed to a host or consortium** if one adopts it as
an integrity layer. Governance is intentionally lightweight precisely so that
this transfer is cheap: there is no entanglement to unwind. Until such a
transfer, the editor maintains it; if the project is wound down, it enters a
documented dormant state with all artifacts left published and forkable rather
than deleted.

## How to participate

- Open an Issue or Discussion on `studio-11-co/falsify`.
- For specification or regulatory-mapping feedback, email `hello@falsify.dev`.
- Proposals that come with a runnable conformance vector or a worked example
  carry the most weight.

---

*This document describes the project's current reality, not an aspiration. It
will be updated if and when the governance structure actually changes — not
before.*
