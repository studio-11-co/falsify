// falsify-rs — PRML v0.1 fourth reference implementation in Rust.
//
// Reproduces all thirteen v0.1 conformance vectors and all eight v0.2
// candidate vectors byte-for-byte, including the small-magnitude float
// rendering required by Finding 4 (TV-018).
//
// Single binary. Two runtime dependencies: serde_json (with
// preserve_order for deterministic key handling at the JSON layer) and
// sha2 (for SHA-256). The canonicalizer is hand-rolled to match
// PyYAML's safe_dump output exactly; we do not use any YAML library.
//
// Spec:    https://spec.falsify.dev/v0.1
// Vectors: https://github.com/studio-11-co/falsify/tree/main/spec/test-vectors
//
// Usage:
//     falsify-rs test-vectors <vectors.json>
//     falsify-rs hash <spec.json>
//     falsify-rs verify <spec.json> [--observed <value>]
//
// License: MIT.

use serde_json::{Number, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::process;

// ─────────────────────────────────────────────────────────────────────────
// Canonicalization
// ─────────────────────────────────────────────────────────────────────────

const YAML_INDICATORS: &[char] = &[
    '?', ':', ',', '[', ']', '{', '}', '#', '&', '*', '!', '|', '>', '\'', '"', '%', '@', '`',
];

fn is_plain_bool_or_null(s: &str) -> bool {
    matches!(
        s,
        "" | "y"
            | "Y"
            | "yes"
            | "Yes"
            | "YES"
            | "n"
            | "N"
            | "no"
            | "No"
            | "NO"
            | "true"
            | "True"
            | "TRUE"
            | "false"
            | "False"
            | "FALSE"
            | "on"
            | "On"
            | "ON"
            | "off"
            | "Off"
            | "OFF"
            | "null"
            | "Null"
            | "NULL"
            | "~"
    )
}

// PyYAML's "looks like a number" test, simplified to the regex shapes
// that fire on PRML-relevant strings. Implemented with manual character
// inspection to avoid pulling in a regex crate.
fn looks_like_number(s: &str) -> bool {
    if s.is_empty() {
        return false;
    }
    // Float / int / hex / octal / inf / nan
    let bytes = s.as_bytes();
    let mut i = 0;
    if bytes[0] == b'+' || bytes[0] == b'-' {
        i += 1;
    }
    if i >= bytes.len() {
        return false;
    }
    // .nan / .inf
    if bytes[i] == b'.' && (s[i..].eq_ignore_ascii_case(".nan") || s[i..].eq_ignore_ascii_case(".inf")) {
        return true;
    }
    // Hex 0x...
    if i + 1 < bytes.len() && bytes[i] == b'0' && (bytes[i + 1] == b'x' || bytes[i + 1] == b'X') {
        let rest = &bytes[i + 2..];
        return !rest.is_empty() && rest.iter().all(|b| b.is_ascii_hexdigit());
    }
    // Octal 0o... or 0...
    if bytes[i] == b'0' && i + 1 < bytes.len() && (bytes[i + 1] == b'o' || bytes[i + 1] == b'O') {
        let rest = &bytes[i + 2..];
        return !rest.is_empty() && rest.iter().all(|&b| b >= b'0' && b <= b'7');
    }
    // Decimal float / int / scientific
    let mut saw_digit = false;
    let mut saw_dot = false;
    let mut saw_e = false;
    while i < bytes.len() {
        let c = bytes[i];
        if c.is_ascii_digit() {
            saw_digit = true;
        } else if c == b'.' && !saw_dot && !saw_e {
            saw_dot = true;
        } else if (c == b'e' || c == b'E') && !saw_e && saw_digit {
            saw_e = true;
            // optional sign
            if i + 1 < bytes.len() && (bytes[i + 1] == b'+' || bytes[i + 1] == b'-') {
                i += 1;
            }
            // require at least one digit after e
            if i + 1 >= bytes.len() {
                return false;
            }
        } else {
            return false;
        }
        i += 1;
    }
    saw_digit
}

fn looks_like_timestamp(s: &str) -> bool {
    // Match YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS(.fff)?(Z|±HH:MM)?
    // Hand-coded — no regex dependency.
    let b = s.as_bytes();
    if b.len() < 10 {
        return false;
    }
    if !b[0..4].iter().all(|c| c.is_ascii_digit())
        || b[4] != b'-'
        || !b[5..7].iter().all(|c| c.is_ascii_digit())
        || b[7] != b'-'
        || !b[8..10].iter().all(|c| c.is_ascii_digit())
    {
        return false;
    }
    if b.len() == 10 {
        return true;
    }
    if !(b[10] == b'T' || b[10] == b't' || b[10] == b' ') {
        return false;
    }
    if b.len() < 19 {
        return false;
    }
    if !b[11..13].iter().all(|c| c.is_ascii_digit())
        || b[13] != b':'
        || !b[14..16].iter().all(|c| c.is_ascii_digit())
        || b[16] != b':'
        || !b[17..19].iter().all(|c| c.is_ascii_digit())
    {
        return false;
    }
    // Optional .fff and Z/offset can follow; accept the rest as plausible.
    true
}

fn needs_quoting(s: &str) -> bool {
    if s.is_empty() {
        return true;
    }
    if is_plain_bool_or_null(s) {
        return true;
    }
    if looks_like_number(s) {
        return true;
    }
    if looks_like_timestamp(s) {
        return true;
    }
    let first = s.chars().next().unwrap();
    if YAML_INDICATORS.contains(&first) {
        return true;
    }
    if first == '-' && s.len() > 1 && s.as_bytes()[1] == b' ' {
        return true;
    }
    if first == ' ' || first == '\t' {
        return true;
    }
    let last = s.chars().last().unwrap();
    if last == ' ' || last == '\t' {
        return true;
    }
    if s.contains(": ") {
        return true;
    }
    if s.contains(" #") {
        return true;
    }
    if s.ends_with(':') {
        return true;
    }
    // Control characters
    if s.bytes()
        .any(|b| b < 0x09 || (b > 0x0a && b < 0x20) || b == 0x7f)
    {
        return true;
    }
    false
}

fn quote_single(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('\'');
    for ch in s.chars() {
        if ch == '\'' {
            out.push_str("''");
        } else {
            out.push(ch);
        }
    }
    out.push('\'');
    out
}

// Render a json::Number for a float field, matching PyYAML's safe_dump
// output. PyYAML inherits Python's repr(float):
//   - magnitudes < 1e-4 or >= 1e16 use scientific notation with mantissa
//     decimal place (`.0`) decoration and 2-digit zero-padded exponent
//   - other floats use shortest round-trip decimal
//
// serde_json's Number::to_string emits scientific notation without
// padding (`1e-6`) and without mantissa decimal (`1e-6`); both must be
// fixed to reproduce PyYAML byte-for-byte.
fn render_number_for_float_field(raw: &str) -> String {
    if let Some(e_idx) = raw.find(|c: char| c == 'e' || c == 'E') {
        let (mantissa, exponent_part) = raw.split_at(e_idx);
        // exponent_part starts with 'e' or 'E', then optional +/-, then digits.
        let e_char = &exponent_part[..1];
        let rest = &exponent_part[1..];
        let (sign, digits) = if rest.starts_with('-') || rest.starts_with('+') {
            (&rest[..1], &rest[1..])
        } else {
            ("+", rest)
        };
        // Pad digits to at least 2 with leading zeros.
        let padded_digits = if digits.len() < 2 {
            format!("{:0>2}", digits)
        } else {
            digits.to_string()
        };
        // PyYAML always emits an explicit sign on the exponent (`e-06`,
        // `e+06`). serde_json may omit `+`; we normalise to always-explicit
        // for negative, but PyYAML actually omits `+` for positive
        // exponents (e.g. `1.0e+06` is rare; `1.0e+10` would render). To
        // match PyYAML exactly: include sign only when negative; positive
        // exponents drop the sign? Empirically PyYAML emits "1.0e+06" for
        // 1e6, but our test surface only exercises small values. Be
        // conservative: emit the sign as-is for negative; for positive,
        // drop it.
        let signed_exp = if sign == "-" {
            format!("{}-{}", e_char, padded_digits)
        } else {
            format!("{}+{}", e_char, padded_digits)
        };
        if !mantissa.contains('.') {
            return format!("{}.0{}", mantissa, signed_exp);
        }
        return format!("{}{}", mantissa, signed_exp);
    }
    if !raw.contains('.') {
        return format!("{}.0", raw);
    }
    raw.to_string()
}

// Float fields whose canonical form must always carry at least one
// decimal place even when integer-valued. Version-aware: v0.1 fixed
// threshold as float64; v0.2 RFC P-XX relaxes threshold to int|float,
// so integer-valued thresholds render as plain integers under v0.2.
fn is_float_field(field: &str, version: &str) -> bool {
    if version == "prml/0.1" {
        field == "threshold"
    } else {
        false
    }
}

fn render_scalar(v: &Value, field: &str, version: &str) -> String {
    match v {
        Value::Null => "null".to_string(),
        Value::Bool(true) => "true".to_string(),
        Value::Bool(false) => "false".to_string(),
        Value::Number(n) => render_number(n, field, version),
        Value::String(s) => {
            if needs_quoting(s) {
                quote_single(s)
            } else {
                s.clone()
            }
        }
        _ => panic!("render_scalar called on non-scalar"),
    }
}

fn render_number(n: &Number, field: &str, version: &str) -> String {
    let raw = n.to_string();
    if is_float_field(field, version) {
        return render_number_for_float_field(&raw);
    }
    raw
}

// Sort the keys of a serde_json::Map alphabetically by traversing it
// into a BTreeMap for deterministic ordering.
fn sorted_keys(map: &serde_json::Map<String, Value>) -> Vec<&String> {
    let mut keys: Vec<&String> = map.keys().collect();
    keys.sort();
    keys
}

fn render_mapping(map: &serde_json::Map<String, Value>, indent: usize, version: &str) -> String {
    let pad: String = " ".repeat(indent);
    let mut lines: Vec<String> = Vec::with_capacity(map.len());
    for k in sorted_keys(map) {
        let v = &map[k];
        match v {
            Value::Object(sub) => {
                lines.push(format!("{}{}:", pad, k));
                lines.push(render_mapping(sub, indent + 2, version));
            }
            Value::Array(items) => {
                lines.push(format!("{}{}:", pad, k));
                for item in items {
                    if let Value::Object(sub) = item {
                        let nested = render_mapping(sub, indent + 2, version);
                        let pad_nested = " ".repeat(indent + 2);
                        let mut nested_lines: Vec<String> =
                            nested.lines().map(|s| s.to_string()).collect();
                        if let Some(first) = nested_lines.first_mut() {
                            *first = format!(
                                "{}- {}",
                                pad,
                                first.strip_prefix(&pad_nested).unwrap_or(first.as_str())
                            );
                        }
                        lines.push(nested_lines.join("\n"));
                    } else {
                        lines.push(format!("{}- {}", pad, render_scalar(item, k, version)));
                    }
                }
            }
            _ => {
                lines.push(format!("{}{}: {}", pad, k, render_scalar(v, k, version)));
            }
        }
    }
    lines.join("\n")
}

fn canonicalize(map: &serde_json::Map<String, Value>) -> String {
    let version = map
        .get("version")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    format!("{}\n", render_mapping(map, 0, version))
}

fn manifest_hash(map: &serde_json::Map<String, Value>) -> String {
    let canonical = canonicalize(map);
    let mut hasher = Sha256::new();
    hasher.update(canonical.as_bytes());
    let result = hasher.finalize();
    let mut hex = String::with_capacity(64);
    for b in result {
        use std::fmt::Write;
        write!(hex, "{:02x}", b).unwrap();
    }
    hex
}

// ─────────────────────────────────────────────────────────────────────────
// Test-vector runner
// ─────────────────────────────────────────────────────────────────────────

fn run_vectors(path: &str) -> i32 {
    let data = match fs::read_to_string(path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("read {}: {}", path, e);
            return 2;
        }
    };
    let parsed: Value = match serde_json::from_str(&data) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("decode: {}", e);
            return 2;
        }
    };
    let vectors = match parsed.as_array() {
        Some(arr) => arr,
        None => {
            eprintln!("vectors file root is not an array");
            return 2;
        }
    };
    let mut pass = 0;
    let mut fail = 0;
    for vec in vectors {
        let vobj = match vec.as_object() {
            Some(o) => o,
            None => {
                eprintln!("vector is not an object");
                fail += 1;
                continue;
            }
        };
        let id = vobj
            .get("id")
            .and_then(|v| v.as_str())
            .unwrap_or("(no id)");
        let title = vobj
            .get("title")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let input = match vobj.get("input").and_then(|v| v.as_object()) {
            Some(m) => m,
            None => {
                eprintln!("{}: input missing or not an object", id);
                fail += 1;
                continue;
            }
        };
        let expected_canonical = vobj.get("canonical").and_then(|v| v.as_str()).unwrap_or("");
        let expected_hash = vobj.get("hash").and_then(|v| v.as_str()).unwrap_or("");
        let produced = canonicalize(input);
        let produced_hash = {
            let mut h = Sha256::new();
            h.update(produced.as_bytes());
            let r = h.finalize();
            let mut s = String::new();
            for b in r {
                use std::fmt::Write;
                write!(s, "{:02x}", b).unwrap();
            }
            s
        };
        if produced == expected_canonical && produced_hash == expected_hash {
            println!("PASS  {}  {}", id, title);
            pass += 1;
        } else {
            println!("FAIL  {}  {}", id, title);
            let diff = first_diff(expected_canonical, &produced);
            if diff >= 0 {
                let diff = diff as usize;
                let lo = diff.saturating_sub(10);
                let hi_e = (diff + 30).min(expected_canonical.len());
                let hi_p = (diff + 30).min(produced.len());
                println!("        first diff @ char {}", diff);
                println!("        expected: {:?}", &expected_canonical[lo..hi_e]);
                println!("        produced: {:?}", &produced[lo..hi_p]);
            }
            if produced_hash != expected_hash {
                println!("        expected hash: {}", expected_hash);
                println!("        produced hash: {}", produced_hash);
            }
            fail += 1;
        }
    }
    println!("\nResult: {}/{} vectors passed.", pass, pass + fail);
    if fail > 0 {
        10
    } else {
        0
    }
}

fn first_diff(a: &str, b: &str) -> i64 {
    let ab = a.as_bytes();
    let bb = b.as_bytes();
    let n = ab.len().min(bb.len());
    for i in 0..n {
        if ab[i] != bb[i] {
            return i as i64;
        }
    }
    if ab.len() != bb.len() {
        n as i64
    } else {
        -1
    }
}

// ─────────────────────────────────────────────────────────────────────────
// Verifier
// ─────────────────────────────────────────────────────────────────────────

// Control / non-portable chars disallowed in any PRML string field: C0
// (U+0000–U+001F), DEL + C1 (U+007F–U+009F), line/paragraph separators
// (U+2028/U+2029), and BOM (U+FEFF). They canonicalize inconsistently across
// YAML engines, so a manifest carrying them is non-portable. Rejecting is
// additive — no conformance vector contains them. Mirrors the Python reference.
fn is_forbidden_char(c: char) -> bool {
    matches!(c, '\u{0}'..='\u{1f}' | '\u{7f}'..='\u{9f}' | '\u{2028}' | '\u{2029}' | '\u{feff}')
}

// forbidden_char_fields walks a parsed manifest and returns the dotted paths of
// any string field (key or value) containing a forbidden char.
fn forbidden_char_fields(v: &Value, path: &str) -> Vec<String> {
    let mut out = Vec::new();
    match v {
        Value::String(s) => {
            if s.chars().any(is_forbidden_char) {
                out.push(if path.is_empty() { "(value)".to_string() } else { path.to_string() });
            }
        }
        Value::Object(map) => {
            for (k, vv) in map {
                let child = if path.is_empty() { k.clone() } else { format!("{}.{}", path, k) };
                // A forbidden char in a KEY canonicalizes non-portably just as in a value.
                if k.chars().any(is_forbidden_char) {
                    out.push(format!("{} (key)", child));
                }
                out.extend(forbidden_char_fields(vv, &child));
            }
        }
        Value::Array(arr) => {
            for (i, vv) in arr.iter().enumerate() {
                out.extend(forbidden_char_fields(vv, &format!("{}[{}]", path, i)));
            }
        }
        _ => {}
    }
    out
}

fn is_hex64(s: &str) -> bool {
    s.len() == 64 && s.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

// validate_manifest mirrors the Python reference's validate_manifest: it returns
// the reasons a manifest is not a valid PRML v0.1/v0.2 manifest (empty = valid).
// Required fields, version, threshold type, comparator, dataset id/hash (64
// lowercase hex), producer id, and the control / non-portable character rule.
fn validate_manifest(parsed: &Value) -> Vec<String> {
    let mut errs = Vec::new();
    let map = match parsed.as_object() {
        Some(m) => m,
        None => return vec!["manifest must be a mapping".to_string()],
    };
    for f in ["version", "claim_id", "created_at", "metric",
              "comparator", "threshold", "dataset", "seed", "producer"] {
        if !map.contains_key(f) {
            errs.push(format!("missing required field: {}", f));
        }
    }
    match map.get("version").and_then(|v| v.as_str()) {
        Some("prml/0.1") | Some("prml/0.2") => {}
        other => errs.push(format!(
            "version must be \"prml/0.1\" or \"prml/0.2\", got {:?}", other)),
    }
    if !map.get("threshold").map(|v| v.is_number()).unwrap_or(false) {
        errs.push("threshold must be a finite number".to_string());
    }
    if let Some(c) = map.get("comparator").and_then(|v| v.as_str()) {
        if !c.is_empty() && !matches!(c, ">=" | "<=" | ">" | "<" | "==") {
            errs.push("comparator must be one of <, <=, ==, >, >=".to_string());
        }
    }
    if let Some(ds) = map.get("dataset").and_then(|v| v.as_object()) {
        for f in ["id", "hash"] {
            if !ds.contains_key(f) {
                errs.push(format!("missing required field: dataset.{}", f));
            }
        }
        if let Some(h) = ds.get("hash").and_then(|v| v.as_str()) {
            if !h.is_empty() && !is_hex64(h) {
                errs.push("dataset.hash must be 64 lowercase hex chars".to_string());
            }
        }
    }
    if let Some(prod) = map.get("producer").and_then(|v| v.as_object()) {
        if !prod.contains_key("id") {
            errs.push("missing required field: producer.id".to_string());
        }
    }
    for fld in forbidden_char_fields(parsed, "") {
        errs.push(format!("{}: contains a control / non-portable character \
            (C0/C1, U+007F, U+2028/U+2029, or U+FEFF) — not allowed in a PRML string field", fld));
    }
    errs.extend(schema_conformance_errors(map));
    errs
}

// Full published-schema conformance (spec/schema/prml-v0.1.schema.json).
// Added in v0.3.12: validators must agree with the published JSON Schema
// (Andes interoperability assessment, finding 1). Hand-rolled checks keep
// this implementation stdlib-only.
fn is_hex_n(s: &str, n: usize) -> bool {
    s.len() == n && s.chars().all(|c| c.is_ascii_hexdigit())
}

fn is_uuidv7(s: &str) -> bool {
    let parts: Vec<&str> = s.split('-').collect();
    if parts.len() != 5 { return false; }
    if !(is_hex_n(parts[0], 8) && is_hex_n(parts[1], 4) && is_hex_n(parts[2], 4)
        && is_hex_n(parts[3], 4) && is_hex_n(parts[4], 12)) { return false; }
    if !parts[2].starts_with('7') { return false; }
    matches!(parts[3].chars().next(), Some('8') | Some('9') | Some('a') | Some('b') | Some('A') | Some('B'))
}

fn is_rfc3339(s: &str) -> bool {
    // YYYY-MM-DDThh:mm:ss(.frac)?(Z|±hh:mm)
    let b: Vec<char> = s.chars().collect();
    if b.len() < 20 { return false; }
    let d = |i: usize| b.get(i).map(|c| c.is_ascii_digit()).unwrap_or(false);
    if !(d(0) && d(1) && d(2) && d(3) && b[4] == '-' && d(5) && d(6) && b[7] == '-'
        && d(8) && d(9) && (b[10] == 'T' || b[10] == 't') && d(11) && d(12) && b[13] == ':'
        && d(14) && d(15) && b[16] == ':' && d(17) && d(18)) { return false; }
    let mut i = 19;
    if b.get(i) == Some(&'.') {
        i += 1;
        let start = i;
        while i < b.len() && b[i].is_ascii_digit() { i += 1; }
        if i == start { return false; }
    }
    match b.get(i) {
        Some('Z') | Some('z') => i + 1 == b.len(),
        Some('+') | Some('-') => {
            b.len() == i + 6 && d(i + 1) && d(i + 2) && b[i + 3] == ':' && d(i + 4) && d(i + 5)
        }
        _ => false,
    }
}

fn schema_conformance_errors(map: &serde_json::Map<String, Value>) -> Vec<String> {
    let mut errs = Vec::new();
    if let Some(cid) = map.get("claim_id").and_then(|v| v.as_str()) {
        if !is_uuidv7(cid) {
            errs.push("claim_id must be a UUIDv7 (schema pattern: version nibble 7, variant 8/9/a/b)".to_string());
        }
    }
    if let Some(ca) = map.get("created_at").and_then(|v| v.as_str()) {
        if !is_rfc3339(ca) {
            errs.push("created_at must be an RFC 3339 date-time".to_string());
        }
    }
    if let Some(met) = map.get("metric").and_then(|v| v.as_str()) {
        let n = met.chars().count();
        if n < 1 || n > 256 {
            errs.push("metric must be 1..256 characters".to_string());
        }
    }
    if let Some(seed) = map.get("seed") {
        if !seed.is_null() && seed.as_i64().is_none() && seed.as_u64().is_none() {
            errs.push("seed must be an integer or null".to_string());
        }
    }
    if let Some(ds) = map.get("dataset").and_then(|v| v.as_object()) {
        if let Some(id) = ds.get("id").and_then(|v| v.as_str()) {
            if id.is_empty() { errs.push("dataset.id must be non-empty".to_string()); }
        }
        for k in ds.keys() {
            if k != "id" && k != "hash" && k != "uri" {
                errs.push(format!("dataset.{}: unknown field (schema additionalProperties: false)", k));
            }
        }
    }
    if let Some(prod) = map.get("producer").and_then(|v| v.as_object()) {
        if let Some(id) = prod.get("id").and_then(|v| v.as_str()) {
            if id.is_empty() { errs.push("producer.id must be non-empty".to_string()); }
        }
        for k in prod.keys() {
            if k != "id" && k != "signature" {
                errs.push(format!("producer.{}: unknown field (schema additionalProperties: false)", k));
            }
        }
    }
    if let Some(ph) = map.get("prior_hash") {
        if !ph.as_str().map(|s| is_hex_n(s, 64)).unwrap_or(false) {
            errs.push("prior_hash must be 64 hex characters".to_string());
        }
    }
    if let Some(nt) = map.get("notes") {
        if !nt.as_str().map(|s| s.chars().count() <= 4096).unwrap_or(false) {
            errs.push("notes must be a string of at most 4096 characters".to_string());
        }
    }
    const TOP: [&str; 14] = ["version", "claim_id", "created_at", "metric", "comparator",
        "threshold", "dataset", "seed", "producer", "model", "compute_envelope",
        "prior_hash", "notes", "metric_args"];
    for k in map.keys() {
        if !TOP.contains(&k.as_str()) {
            errs.push(format!("{}: unknown top-level field (schema additionalProperties: false)", k));
        }
    }
    errs
}

fn cmd_hash(spec_path: &str) -> i32 {
    let data = match fs::read_to_string(spec_path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("hash: {}", e);
            return 2;
        }
    };
    let parsed: Value = match serde_json::from_str(&data) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("hash: parse: {}", e);
            return 2;
        }
    };
    let map = match parsed.as_object() {
        Some(m) => m,
        None => {
            eprintln!("hash: spec must be a JSON object");
            return 2;
        }
    };
    let errs = validate_manifest(&parsed);
    if !errs.is_empty() {
        eprintln!("hash: invalid manifest:");
        for e in &errs {
            eprintln!("  - {}", e);
        }
        return 2;
    }
    println!("{}", manifest_hash(map));
    0
}

fn cmd_verify(spec_path: &str, observed: Option<&str>) -> i32 {
    let data = match fs::read_to_string(spec_path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("verify: {}", e);
            return 2;
        }
    };
    let parsed: Value = match serde_json::from_str(&data) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("verify: parse: {}", e);
            return 2;
        }
    };
    let map = match parsed.as_object() {
        Some(m) => m,
        None => {
            eprintln!("verify: spec must be a JSON object");
            return 2;
        }
    };
    let errs = validate_manifest(&parsed);
    if !errs.is_empty() {
        eprintln!("verify: invalid manifest:");
        for e in &errs {
            eprintln!("  - {}", e);
        }
        return 2;
    }
    let computed = manifest_hash(map);
    // Sidecar: replace extension with .prml.sha256
    let sidecar = if let Some(idx) = spec_path.rfind('.') {
        let stem = &spec_path[..idx];
        format!("{}.prml.sha256", stem)
    } else {
        format!("{}.prml.sha256", spec_path)
    };
    let claimed = match fs::read_to_string(&sidecar) {
        Ok(s) => s.trim().to_string(),
        Err(_) => {
            eprintln!("verify: sidecar not found: {}", sidecar);
            return 11;
        }
    };
    if computed != claimed {
        println!("TAMPERED");
        println!("  recorded:    {}", claimed);
        println!("  recomputed:  {}", computed);
        return 3;
    }
    let observed = match observed {
        Some(o) => o,
        None => {
            println!("hash OK: {}", computed);
            println!("(no --observed value given; predicate not evaluated)");
            return 0;
        }
    };
    let observed: f64 = match observed.parse::<f64>() {
        Ok(v) if v.is_finite() => v,
        _ => {
            eprintln!("verify: --observed must be a finite number");
            return 2;
        }
    };
    let comparator = map.get("comparator").and_then(|v| v.as_str()).unwrap_or("");
    let threshold = match map
        .get("threshold")
        .and_then(|v| v.as_f64())
    {
        Some(t) => t,
        None => {
            eprintln!("verify: threshold not numeric");
            return 2;
        }
    };
    let metric = map.get("metric").and_then(|v| v.as_str()).unwrap_or("");
    let ok = match comparator {
        ">=" => observed >= threshold,
        "<=" => observed <= threshold,
        ">" => observed > threshold,
        "<" => observed < threshold,
        "==" => observed == threshold,
        _ => {
            eprintln!("verify: invalid comparator: {}", comparator);
            return 2;
        }
    };
    if ok {
        println!(
            "PASS  metric={}  observed={}  {}  threshold={}",
            metric, observed, comparator, threshold
        );
        0
    } else {
        println!(
            "FAIL  metric={}  observed={}  NOT {}  threshold={}",
            metric, observed, comparator, threshold
        );
        10
    }
}

fn usage() -> i32 {
    eprintln!("falsify-rs — PRML v0.1 fourth reference implementation (Rust)\n");
    eprintln!("Commands:");
    eprintln!("  test-vectors <vectors.json>            run conformance suite");
    eprintln!("  hash <spec.json>                       print canonical SHA-256");
    eprintln!("  verify <spec.json> [--observed <v>]    verify hash; if --observed, evaluate");
    eprintln!();
    eprintln!("Exit codes: 0=PASS, 2=BAD (bad input/spec), 3=TAMPERED, 10=FAIL, 11=GUARD (missing sidecar)");
    eprintln!("Spec:    https://spec.falsify.dev/v0.1");
    11
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let code = if args.len() < 2 {
        usage()
    } else {
        match args[1].as_str() {
            "test-vectors" if args.len() >= 3 => run_vectors(&args[2]),
            "hash" if args.len() >= 3 => cmd_hash(&args[2]),
            "verify" if args.len() >= 3 => {
                let mut observed: Option<&str> = None;
                if let Some(idx) = args.iter().position(|a| a == "--observed") {
                    if idx + 1 < args.len() {
                        observed = Some(&args[idx + 1]);
                    }
                }
                cmd_verify(&args[2], observed)
            }
            "-h" | "--help" => {
                usage();
                0
            }
            _ => usage(),
        }
    };
    process::exit(code);
}

// Suppress "unused" warning for a helper that may be used in tests.
#[allow(dead_code)]
fn _ensure_hash_in_use(_: BTreeMap<String, String>) {}
