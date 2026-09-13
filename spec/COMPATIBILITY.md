# Compatibility and Deprecation Policy

**Status: adopted 2026-09-13 by the editor; binding.** Linked from PRML-v0.1.md
"Status of This Memo". Canonical URL: https://spec.falsify.dev/COMPATIBILITY.md Applies to the PRML specification, its conformance corpus, the
reference implementations distributed as packages (`falsify` on PyPI, `falsify-js`
on npm), and the public registry.

## 1. Two version lines, versioned separately

- **The specification** is versioned as `prml/MAJOR.MINOR` and appears in every
  manifest's `version` field. A manifest is interpreted under the rules of the
  version it names, forever.
- **Each package** is versioned with semantic versioning independently of the
  specification and of the other packages, and declares which specification
  versions it implements. `falsify 1.4.2` and `falsify-js 1.1.7` implementing
  `prml/0.1` and `prml/0.2` is the expected shape, not an inconsistency.

## 2. What a specification version promises

**PATCH-level change to the specification (an erratum)** may clarify text, add a
rejection requirement for input that was never valid, add vectors, or add a
constraint that every existing valid manifest already satisfies. It **never**
changes the canonical byte sequence or the digest of any manifest that was valid
before it. Every erratum is dated in the specification itself.

**MINOR (`prml/0.3`)** may add optional fields and new rules that apply only to
manifests naming the new version. Because the schema declares
`additionalProperties: false`, a manifest naming an older version is unaffected: it
does not gain the fields and its bytes do not move.

**MAJOR (`prml/1.0`)** may change canonicalization, remove fields, or change the
meaning of a field — again only for manifests naming the new version.

**The invariant across all three:** a manifest that verified under `prml/X.Y` on
the day it was committed verifies under `prml/X.Y` on every later day, with every
later release of every conforming implementation. Implementations MUST keep the
rules of every specification version they have ever supported; dropping support
for a specification version is a MAJOR change to the implementation and is
announced under §4.

## 3. What a package version promises

- **PATCH** — no change in behaviour on any input; documentation, packaging,
  performance, dependency updates that do not alter output.
- **MINOR** — backwards-compatible additions (a new command, option, output field,
  supported specification version). Existing invocations produce identical output.
  **A change in canonical output for any input is at least MINOR while the package
  is pre-1.0, and is called out in the changelog with the inputs affected** (as
  `falsify-js` 0.2.0 was).
- **MAJOR** — anything that breaks an existing invocation: a renamed command or
  option, a changed exit code, a changed output format, a dropped specification
  version, a dropped runtime.

From `1.0.0` the public API of each package — command names, options, exit codes,
output formats, the exported functions named in its README — is frozen for the
life of `1.x`.

## 4. Deprecation

Nothing is removed without all of the following:

1. **Announcement** in the changelog of a release at least **two MINOR releases**
   before removal (or six months, whichever is longer), naming the replacement.
2. **A runtime warning** from the deprecated command or option, on stderr, that
   names the release in which it will be removed and the replacement.
3. **A migration note** in the changelog of the removing release.
4. **The previous MINOR line stays supported** — security fixes and conformance
   corrections — until the removing release ships plus six months.

A specification version is never "removed"; implementations may drop *support*
for one only under §3 MAJOR and §4.

## 5. Conformance corpus

Vectors are added, never changed. A published vector's `input`, `canonical` and
`hash` are permanent. If a vector is found to be wrong, it is **withdrawn** with a
dated note and a replacement id; the withdrawn entry stays in the file marked
`withdrawn: <date>`. Counts quoted on public surfaces name the suite they count.

## 6. The public registry

- A committed record is never deleted or altered, with one exception: a
  `producer.id` that turns out to contain personal contact details is handled as a
  removal request (see the registry's SECURITY.md).
- Receipts stay verifiable across signing-key rotations; every key ever used is
  published at `/pubkeys` with its validity window.
- The canonicalizer the registry runs is the JavaScript reference at a pinned
  version, and the copy served to browsers is generated from the same source.
  When the canonicalizer changes, the registry's deploy chain re-derives every
  stored record whose bytes are public against the new canonicalizer before
  deploying (`scripts/check-records.mjs`); a record that would no longer re-derive
  blocks the deploy. Sealed records cannot be checked by anyone until revealed,
  by construction.

## 7. What this policy does not cover

The workflow engine (`falsify-engine`) is a separate tool with its own schema and
carries no compatibility promise beyond its changelog. The HF playground is a demo.
Anything marked *informative* in the specification (block sequences, C7) may change
without notice until a vector pins it.

---
