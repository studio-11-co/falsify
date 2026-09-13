# v0.3 RFC issue: the detached signature sidecar

**Status:** backlog, opened 2026-09-13 by the disposition of the §2.3.3
forward-promise ("v0.2 normatively adopts this sidecar convention" → re-scoped:
format normative when present, presence optional). Inputs welcome.

## Problem

v0.1 §2.3.3 says a signature, when present, MUST be a detached signature over the
**canonical bytes** of the manifest (erratum 2026-05-02: not over the hash), and
SHOULD live in a sidecar `<claim_id>.prml.sig`. It does not say what is *in* that
file, which algorithms are admissible, how the key is identified, or what a
verifier does on encountering one. Four reference implementations and one
registry exist; none reads a sidecar. No vector exercises one.

There is also a defect in §2.3.3 as written that this issue inherits rather than
fixes: the optional `producer.signature` **field** is inside the manifest, so the
manifest's canonical bytes include it, so it cannot be a signature over those
bytes. Either the field signs a canonicalization that omits it (not specified),
or the field cannot carry what §2.3.3 says it carries. The sidecar has no such
problem — it is outside the bytes — which is why this issue treats the sidecar as
the primary carrier and leaves the in-manifest field to `02-producer-struct.md`.

## Decision taken (2026-09-13)

- Presence of a signature stays **optional** at every conformance level.
- If a sidecar is present its **format is normative** (below).
- A verifier **MAY** verify sidecars. A verifier that does **MUST** verify over
  the canonical bytes it computed itself, **MUST** treat a signature that
  verifies only over the hash string as invalid (the withdrawn practice), and
  **MUST NOT** change the hash or comparator verdict based on the signature —
  signature failure is reported as its own outcome.
- One test vector, generated below, with a public test key.

## Proposed sidecar format — `prml-sig/0`

A UTF-8 text file, LF line endings, four lines, no trailing whitespace:

```
prml-sig/0
alg: ed25519
pubkey: 24d19161c825859b9e028dbaad440e4391e21e10b6e1f4fd79528eac0870daf1
sig: iMaOUz0Uha4Qc6bfE2OcLZLNrn7in9r/GG2nbFW+nCpgzfZLD55VZ47vHFqK8I5iFxtQd7SfCKNsmX+ZukbaAQ==
```

| Line | Rule |
|---|---|
| 1 | literal `prml-sig/0` |
| 2 | `alg: ` + one of `ed25519`, `minisign`, `openpgp` |
| 3 | `pubkey: ` + lowercase hex of the raw public key (32 bytes for `ed25519`), **or** `key_id: ` + `sha256:` fingerprint as in `02-producer-struct.md` when the key is distributed out of band |
| 4 | `sig: ` + base64 (RFC 4648, padded) of the detached signature; for `minisign` and `openpgp` the base64 of the tool's native detached-signature bytes |

Verifier behaviour, when it chooses to verify: read the manifest, canonicalize
(§3), verify `sig` over exactly those bytes with `alg` and `pubkey`. An
unsupported `alg` is reported as *unverified*, not as failure. A sidecar whose
signature does not verify is reported as **signature invalid**; the proposed
exit code is `3` (the bytes' authenticity failed, the nearest existing meaning)
— see open questions.

## Test vector (public test key — never use for anything real)

The key is derived from a published seed so that anyone can regenerate it. It
authenticates nothing.

| | |
|---|---|
| manifest | `spec/test-vectors/v0.1/vectors/TV-001/manifest.yaml` (TV-001, canonical bytes as published) |
| seed (hex) | `5f30546c265f6b96af66401b159fefbae7741fbd05700696cecc7a0fb6a5c261` = SHA-256 of the ASCII string `prml-test-key-01 (public test key, never for real use)` |
| pubkey (hex) | `24d19161c825859b9e028dbaad440e4391e21e10b6e1f4fd79528eac0870daf1` |
| sig over canonical bytes (hex) | `88c68e533d1485ae1073a6df13639c2d92cdae7ee29fdaff186da76c55be9c2a60cdf64b0f9e55678eef1c5a8af08e62171b5077b49f08a36c997f99ba46da01` |
| sig over canonical bytes (base64) | `iMaOUz0Uha4Qc6bfE2OcLZLNrn7in9r/GG2nbFW+nCpgzfZLD55VZ47vHFqK8I5iFxtQd7SfCKNsmX+ZukbaAQ==` |

Expected outcomes for a verifier that verifies sidecars:

| Case | Sidecar | Expected |
|---|---|---|
| SV-001 | the sidecar above, manifest unchanged | **valid** |
| SV-002 | same sidecar, `threshold` changed `0.85` → `0.86` in the manifest | **signature invalid** (and hash mismatch, exit 3) |
| SV-003 | `sig` = signature over the ASCII hash string `1a3466cc…` instead of the bytes (`ceabd93cac9bb5e047b165fbc0e43ff0…`) | **signature invalid** — the withdrawn practice |
| SV-004 | `alg: minisign` with any payload, verifier supports only ed25519 | **unverified**, hash verdict unaffected |

Regenerate with Python and `cryptography`:

```python
import hashlib, base64, json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
seed = hashlib.sha256(b"prml-test-key-01 (public test key, never for real use)").digest()
sk = Ed25519PrivateKey.from_private_bytes(seed)
canon = json.load(open("spec/test-vectors/v0.1/test-vectors.json"))[0]["canonical"].encode()
print(base64.b64encode(sk.sign(canon)).decode())
```

## Compatibility

Nothing in this issue touches canonical bytes, digests or validation of the
manifest itself. A sidecar is a separate file; a verifier that ignores sidecars is
unchanged. The `.prml.sha256` sidecar is unaffected.

## Open questions

- **Exit code.** `3` (tampered) reuses the "bytes are not what they claim"
  meaning; `11` (guard) reuses "a producer-declared invariant failed". A new code
  would be cleanest and is a §7 change. Undecided.
- **Naming.** §2.3.3 says `<claim_id>.prml.sig`; the v0.2 ROADMAP (#10) says
  `<name>.prml.sig` next to `<name>.prml.sha256`. Pick one; the vector above uses
  the manifest's filename stem.
- **The in-manifest field.** Whether `producer.signature` signs a canonicalization
  that omits itself, or is dropped in favour of the sidecar, belongs to
  `02-producer-struct.md` and must be settled before either becomes normative.
- **Multiple signatures** (a producer and an auditor): one sidecar with repeated
  `alg/pubkey/sig` blocks, or several files. Undecided.
- **Registry.** Whether `registry.falsify.dev` accepts and displays a sidecar at
  commit time is a registry question, not a specification one.

## Related

- v0.1 §2.3.3 and the erratum of 2026-05-02 (sign over bytes, not the hash)
- Erratum of 2026-09-13 (dispositions), item 2
- `02-producer-struct.md` (structured `producer` with `key_id` / `signature` / `sigstore_bundle`)
- `spec/grammar/README.md` C1–C6 (what "canonical bytes" means precisely)
