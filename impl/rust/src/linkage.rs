// prml-linkage/0 — Rust reference implementation (draft).
//
// Spec: spec/linkage/prml-linkage-0.md. Byte-parity with the Python, JS and
// Go references is asserted by tests/test_linkage_parity.py via the
// `linkage-parity` subcommand (stdin/stdout JSON protocol).

use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::io::Read;

const LINKAGE_VERSION: &str = "prml-linkage/0";
const START_FIELDS: [&str; 4] = ["linkage_version", "manifest_hash", "receipt", "run"];
const FINAL_FIELDS: [&str; 6] = [
    "linkage_version",
    "manifest_hash",
    "receipt",
    "run",
    "start_hash",
    "result",
];
const RUN_FIELDS: [&str; 5] = [
    "dataset_hash",
    "environment",
    "id",
    "model_version",
    "started_at",
];
const RESULT_FIELDS: [&str; 4] = ["digest", "exit_code", "finished_at", "observed"];
const VALID_EXIT_CODES: [i64; 4] = [0, 3, 10, 11];

fn is_hex64_lower(s: &str) -> bool {
    s.len() == 64 && s.chars().all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase())
}

fn linkage_hash(record: &Map<String, Value>) -> String {
    let canonical = super::canonicalize(record);
    let mut hasher = Sha256::new();
    hasher.update(canonical.as_bytes());
    let out = hasher.finalize();
    let mut hex = String::with_capacity(64);
    for b in out {
        use std::fmt::Write;
        write!(hex, "{:02x}", b).unwrap();
    }
    hex
}

// RFC 3339 with mandatory offset ("Z" or +hh:mm) → epoch millis.
// Minimal parser: enough for chronology comparison, no external deps.
fn parse_rfc3339(v: &Value) -> Option<i64> {
    let s = v.as_str()?;
    let bytes = s.as_bytes();
    if bytes.len() < 20 {
        return None;
    }
    let num = |a: usize, b: usize| -> Option<i64> { s.get(a..b)?.parse::<i64>().ok() };
    let (year, month, day) = (num(0, 4)?, num(5, 7)?, num(8, 10)?);
    if bytes[4] != b'-' || bytes[7] != b'-' || (bytes[10] != b'T' && bytes[10] != b't') {
        return None;
    }
    let (hour, minute, second) = (num(11, 13)?, num(14, 16)?, num(17, 19)?);
    if bytes[13] != b':' || bytes[16] != b':' {
        return None;
    }
    if !(1..=12).contains(&month) || !(1..=31).contains(&day) {
        return None;
    }
    if !(0..=23).contains(&hour) || !(0..=59).contains(&minute) || !(0..=60).contains(&second) {
        return None;
    }
    let mut idx = 19;
    let mut frac_ms: i64 = 0;
    if bytes.get(idx) == Some(&b'.') {
        let start = idx + 1;
        let mut end = start;
        while end < bytes.len() && bytes[end].is_ascii_digit() {
            end += 1;
        }
        if end == start {
            return None;
        }
        let digits = &s[start..end.min(start + 3)];
        frac_ms = digits.parse::<i64>().ok()? * 10_i64.pow(3 - digits.len() as u32);
        idx = end;
    }
    let offset_min: i64 = match bytes.get(idx) {
        Some(&b'Z') | Some(&b'z') if idx + 1 == bytes.len() => 0,
        Some(&b'+') | Some(&b'-') if idx + 6 == bytes.len() => {
            let sign = if bytes[idx] == b'+' { 1 } else { -1 };
            if bytes[idx + 3] != b':' {
                return None;
            }
            let oh = num(idx + 1, idx + 3)?;
            let om = num(idx + 4, idx + 6)?;
            sign * (oh * 60 + om)
        }
        _ => return None,
    };
    // Days since epoch via civil-from-days inverse (Howard Hinnant's algorithm).
    let (y, m, d) = (year, month, day);
    let y_adj = if m <= 2 { y - 1 } else { y };
    let era = if y_adj >= 0 { y_adj } else { y_adj - 399 } / 400;
    let yoe = y_adj - era * 400;
    let doy = (153 * (if m > 2 { m - 3 } else { m + 9 }) + 2) / 5 + d - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    let days = era * 146097 + doe - 719468;
    let secs = days * 86400 + hour * 3600 + minute * 60 + second - offset_min * 60;
    Some(secs * 1000 + frac_ms)
}

fn same_field_set(m: &Map<String, Value>, expected: &[&str]) -> bool {
    if m.len() != expected.len() {
        return false;
    }
    expected.iter().all(|k| m.contains_key(*k))
}

fn validate_shape(record: &Map<String, Value>, is_final: bool) -> Vec<String> {
    let mut problems = Vec::new();
    let expected: &[&str] = if is_final { &FINAL_FIELDS } else { &START_FIELDS };
    if record.get("linkage_version").and_then(|v| v.as_str()) != Some(LINKAGE_VERSION) {
        problems.push(format!("linkage_version must be '{}'", LINKAGE_VERSION));
    }
    let missing: Vec<&&str> = expected.iter().filter(|k| !record.contains_key(**k)).collect();
    let extra: Vec<&String> = record
        .keys()
        .filter(|k| !expected.contains(&k.as_str()))
        .collect();
    if !missing.is_empty() {
        problems.push(format!("missing fields: {:?}", missing));
    }
    if !extra.is_empty() {
        problems.push(format!("unknown fields: {:?}", extra));
    }
    match record.get("run").and_then(|v| v.as_object()) {
        None => problems.push("run is not a mapping".to_string()),
        Some(run) => {
            if !same_field_set(run, &RUN_FIELDS) {
                problems.push(format!("run fields must be exactly {:?}", RUN_FIELDS));
            }
            match run.get("dataset_hash").and_then(|v| v.as_str()) {
                Some(dh) if is_hex64_lower(dh) => {}
                _ => problems.push("run.dataset_hash must be 64 lowercase hex chars".to_string()),
            }
            if run.get("started_at").and_then(parse_rfc3339).is_none() {
                problems.push("run.started_at is not RFC 3339".to_string());
            }
        }
    }
    match record.get("manifest_hash").and_then(|v| v.as_str()) {
        Some(mh) if is_hex64_lower(mh) => {}
        _ => problems.push("manifest_hash must be 64 lowercase hex chars".to_string()),
    }
    if is_final {
        match record.get("start_hash").and_then(|v| v.as_str()) {
            Some(sh) if is_hex64_lower(sh) => {}
            _ => problems.push("start_hash must be 64 lowercase hex chars".to_string()),
        }
        match record.get("result").and_then(|v| v.as_object()) {
            None => problems.push("result is not a mapping".to_string()),
            Some(result) => {
                if !same_field_set(result, &RESULT_FIELDS) {
                    problems.push(format!("result fields must be exactly {:?}", RESULT_FIELDS));
                }
                match result.get("exit_code").and_then(|v| v.as_i64()) {
                    Some(ec) if VALID_EXIT_CODES.contains(&ec) => {}
                    _ => problems.push("result.exit_code must be one of 0,3,10,11".to_string()),
                }
                match result.get("digest").and_then(|v| v.as_str()) {
                    Some(dg) if is_hex64_lower(dg) => {}
                    _ => problems.push("result.digest must be 64 lowercase hex chars".to_string()),
                }
                if result.get("finished_at").and_then(parse_rfc3339).is_none() {
                    problems.push("result.finished_at is not RFC 3339".to_string());
                }
            }
        }
    }
    problems
}

fn finalize(
    start: &Map<String, Value>,
    observed: &Value,
    digest: &str,
    exit_code: i64,
    finished_at: &str,
) -> Result<Map<String, Value>, String> {
    let problems = validate_shape(start, false);
    if !problems.is_empty() {
        return Err(format!("invalid start record: {:?}", problems));
    }
    if !VALID_EXIT_CODES.contains(&exit_code) {
        return Err("exit_code must be one of 0,3,10,11".to_string());
    }
    if !is_hex64_lower(digest) {
        return Err("result digest must be 64 lowercase hex chars".to_string());
    }
    if parse_rfc3339(&Value::String(finished_at.to_string())).is_none() {
        return Err("finished_at is not RFC 3339".to_string());
    }
    let mut final_rec = Map::new();
    for key in START_FIELDS {
        final_rec.insert(key.to_string(), start.get(key).cloned().unwrap_or(Value::Null));
    }
    final_rec.insert("start_hash".to_string(), Value::String(linkage_hash(start)));
    let mut result = Map::new();
    // Spec float rule: observed is float64; the canonicalizer's linkage
    // float-field hint renders integer values as "x.0".
    result.insert("observed".to_string(), observed.clone());
    result.insert("digest".to_string(), Value::String(digest.to_string()));
    result.insert("exit_code".to_string(), json!(exit_code));
    result.insert(
        "finished_at".to_string(),
        Value::String(finished_at.to_string()),
    );
    final_rec.insert("result".to_string(), Value::Object(result));
    Ok(final_rec)
}

fn verify(
    final_rec: &Map<String, Value>,
    start: Option<&Map<String, Value>>,
    manifest: Option<&Map<String, Value>>,
) -> Value {
    let mut failures: Vec<Value> = Vec::new();
    let mut skipped: Vec<String> = Vec::new();

    let problems = validate_shape(final_rec, true);
    if !problems.is_empty() {
        let fs: Vec<Value> = problems
            .into_iter()
            .map(|p| json!({"check": "malformed", "detail": p}))
            .collect();
        return json!({"ok": false, "tier": Value::Null, "failures": fs, "skipped": []});
    }

    let mut tier = "L1";
    if let Some(start) = start {
        tier = "L2";
        let sh = linkage_hash(start);
        if final_rec.get("start_hash").and_then(|v| v.as_str()) != Some(sh.as_str()) {
            failures.push(json!({"check": "chain-broken", "detail": "hash(start) != start_hash"}));
        } else {
            let mut view = Map::new();
            for key in START_FIELDS {
                view.insert(key.to_string(), final_rec.get(key).cloned().unwrap_or(Value::Null));
            }
            if super::canonicalize(start) != super::canonicalize(&view) {
                failures.push(json!({"check": "chain-broken", "detail": "start fields differ between start and final"}));
            }
        }
    } else {
        skipped.push("chain (no start record supplied)".to_string());
    }

    let run = final_rec.get("run").and_then(|v| v.as_object()).unwrap();
    let result = final_rec.get("result").and_then(|v| v.as_object()).unwrap();
    let started = run.get("started_at").and_then(parse_rfc3339).unwrap_or(0);
    let finished = result.get("finished_at").and_then(parse_rfc3339).unwrap_or(0);
    if started >= finished {
        failures.push(json!({"check": "chronology", "detail": "started_at is not before finished_at"}));
    }

    if let Some(manifest) = manifest {
        let mh = super::manifest_hash(manifest);
        if final_rec.get("manifest_hash").and_then(|v| v.as_str()) != Some(mh.as_str()) {
            failures.push(json!({"check": "manifest-mismatch", "detail": "manifest_hash differs"}));
        }
        let m_dataset = manifest
            .get("dataset")
            .and_then(|v| v.as_object())
            .and_then(|d| d.get("hash"))
            .and_then(|v| v.as_str());
        if run.get("dataset_hash").and_then(|v| v.as_str()) != m_dataset {
            failures.push(json!({"check": "dataset-mismatch", "detail": "run.dataset_hash != manifest dataset.hash"}));
        }
        let comparator = manifest.get("comparator").and_then(|v| v.as_str());
        let threshold = manifest.get("threshold").and_then(|v| v.as_f64());
        let exit_code = result.get("exit_code").and_then(|v| v.as_i64()).unwrap_or(-1);
        let observed = result.get("observed").and_then(|v| v.as_f64());
        if let (Some(comparator), Some(threshold), Some(observed)) = (comparator, threshold, observed) {
            if exit_code == 0 || exit_code == 10 {
                let passed = match comparator {
                    ">=" => Some(observed >= threshold),
                    "<=" => Some(observed <= threshold),
                    ">" => Some(observed > threshold),
                    "<" => Some(observed < threshold),
                    "==" => Some(observed == threshold),
                    _ => None,
                };
                if let Some(passed) = passed {
                    let expected = if passed { 0 } else { 10 };
                    if exit_code != expected {
                        failures.push(json!({
                            "check": "verdict-mismatch",
                            "detail": format!("observed vs threshold implies exit {}, record says {}", expected, exit_code)
                        }));
                    }
                }
            } else if exit_code == 3 || exit_code == 11 {
                skipped.push("verdict recompute (error exit code)".to_string());
            }
        } else if exit_code == 3 || exit_code == 11 {
            skipped.push("verdict recompute (error exit code)".to_string());
        }
    } else {
        skipped.push("dataset + verdict (no manifest supplied)".to_string());
    }

    json!({"ok": failures.is_empty(), "tier": tier, "failures": failures, "skipped": skipped})
}

// Cross-language parity protocol: one JSON request on stdin, one JSON
// response on stdout. Modes: canonical | finalize | verify.
pub fn cmd_linkage_parity() -> i32 {
    let mut input = String::new();
    if std::io::stdin().read_to_string(&mut input).is_err() {
        eprintln!("linkage-parity: cannot read stdin");
        return 2;
    }
    let req: Value = match serde_json::from_str(&input) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("linkage-parity: bad request: {}", e);
            return 2;
        }
    };
    let mode = req.get("mode").and_then(|v| v.as_str()).unwrap_or("");
    let out = match mode {
        "canonical" => {
            let record = match req.get("record").and_then(|v| v.as_object()) {
                Some(r) => r,
                None => {
                    eprintln!("linkage-parity: record missing");
                    return 2;
                }
            };
            let canonical = super::canonicalize(record);
            let mut hasher = Sha256::new();
            hasher.update(canonical.as_bytes());
            let digest = hasher.finalize();
            let mut hex = String::with_capacity(64);
            for b in digest {
                use std::fmt::Write;
                write!(hex, "{:02x}", b).unwrap();
            }
            json!({"canonical": canonical, "hash": hex})
        }
        "finalize" => {
            let start = match req.get("start").and_then(|v| v.as_object()) {
                Some(s) => s,
                None => {
                    eprintln!("linkage-parity: start missing");
                    return 2;
                }
            };
            let observed = req.get("observed").cloned().unwrap_or(Value::Null);
            let digest = req.get("digest").and_then(|v| v.as_str()).unwrap_or("");
            let exit_code = req.get("exit_code").and_then(|v| v.as_i64()).unwrap_or(-1);
            let finished_at = req.get("finished_at").and_then(|v| v.as_str()).unwrap_or("");
            match finalize(start, &observed, digest, exit_code, finished_at) {
                Ok(final_rec) => {
                    let h = linkage_hash(&final_rec);
                    json!({"final": Value::Object(final_rec), "hash": h})
                }
                Err(e) => {
                    eprintln!("linkage-parity: {}", e);
                    return 2;
                }
            }
        }
        "verify" => {
            let final_rec = match req.get("final").and_then(|v| v.as_object()) {
                Some(f) => f,
                None => {
                    eprintln!("linkage-parity: final missing");
                    return 2;
                }
            };
            let start = req.get("start").and_then(|v| v.as_object());
            let manifest = req.get("manifest").and_then(|v| v.as_object());
            verify(final_rec, start, manifest)
        }
        _ => {
            eprintln!("linkage-parity: unknown mode {}", mode);
            return 2;
        }
    };
    print!("{}", serde_json::to_string(&out).unwrap());
    0
}
