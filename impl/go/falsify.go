// Package main — falsify-go: third reference implementation of PRML v0.1.
//
// Single-file Go implementation. Standard library only.
// Reproduces all 13 PRML v0.1 conformance vectors byte-for-byte.
//
// Spec:    https://spec.falsify.dev/v0.1
// Vectors: https://github.com/studio-11-co/falsify/tree/main/spec/test-vectors
// Python:  https://github.com/studio-11-co/falsify (reference implementation)
// JS:      https://github.com/studio-11-co/falsify/tree/main/impl/js (second)
//
// Usage:
//
//	falsify-go test-vectors <vectors.json>    run conformance suite
//	falsify-go hash <spec.json>               print canonical SHA-256 only
//	falsify-go verify <spec.json> --observed <v>   verify hash; if --observed, evaluate
//
// License: MIT.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

// ─────────────────────────────────────────────────────────────────────────
// Canonicalization
// ─────────────────────────────────────────────────────────────────────────

// yamlIndicators are characters that, when at the start of a string, force
// PyYAML to quote it. We match PyYAML's behaviour to reproduce its bytes.
var yamlIndicators = map[byte]bool{
	'?': true, ':': true, ',': true, '[': true, ']': true,
	'{': true, '}': true, '#': true, '&': true, '*': true,
	'!': true, '|': true, '>': true, '\'': true, '"': true,
	'%': true, '@': true, '`': true,
}

// plainBoolNullSet contains strings that look like bool/null and would be
// re-resolved by a YAML 1.1 parser if left unquoted.
var plainBoolNullSet = map[string]bool{
	"y": true, "Y": true, "yes": true, "Yes": true, "YES": true,
	"n": true, "N": true, "no": true, "No": true, "NO": true,
	"true": true, "True": true, "TRUE": true,
	"false": true, "False": true, "FALSE": true,
	"on": true, "On": true, "ON": true,
	"off": true, "Off": true, "OFF": true,
	"null": true, "Null": true, "NULL": true,
	"~": true, "": true,
}

// numberRegexes — strings matching any of these would be parsed as numbers
// in YAML 1.1 plain-scalar resolution and therefore need quoting.
var (
	floatRegex     = regexp.MustCompile(`^[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?$`)
	intRegex       = regexp.MustCompile(`^[-+]?[0-9]+$`)
	hexRegex       = regexp.MustCompile(`^[-+]?0[xX][0-9a-fA-F]+$`)
	octalRegex     = regexp.MustCompile(`^[-+]?0[oO]?[0-7]+$`)
	infRegex       = regexp.MustCompile(`^[-+]?\.(inf|Inf|INF)$`)
	nanRegex       = regexp.MustCompile(`^\.(nan|NaN|NAN)$`)
	timestampRegex = regexp.MustCompile(`^\d{4}-\d{2}-\d{2}([Tt ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?)?$`)
	controlChars   = regexp.MustCompile("[\x00-\x08\x0b-\x1f\x7f]")
)

func looksLikeNumber(s string) bool {
	return floatRegex.MatchString(s) ||
		intRegex.MatchString(s) ||
		hexRegex.MatchString(s) ||
		octalRegex.MatchString(s) ||
		infRegex.MatchString(s) ||
		nanRegex.MatchString(s)
}

func looksLikeTimestamp(s string) bool {
	return timestampRegex.MatchString(s)
}

func needsQuoting(s string) bool {
	if len(s) == 0 {
		return true
	}
	if plainBoolNullSet[s] {
		return true
	}
	if looksLikeNumber(s) {
		return true
	}
	if looksLikeTimestamp(s) {
		return true
	}
	first := s[0]
	if yamlIndicators[first] {
		return true
	}
	if first == '-' && len(s) > 1 && s[1] == ' ' {
		return true
	}
	if first == ' ' || first == '\t' {
		return true
	}
	last := s[len(s)-1]
	if last == ' ' || last == '\t' {
		return true
	}
	if strings.Contains(s, ": ") {
		return true
	}
	if strings.Contains(s, " #") {
		return true
	}
	if strings.HasSuffix(s, ":") {
		return true
	}
	if controlChars.MatchString(s) {
		return true
	}
	return false
}

// quoteSingle emits PyYAML-style single-quoted scalar: doubles internal '.
func quoteSingle(s string) string {
	return "'" + strings.ReplaceAll(s, "'", "''") + "'"
}

// floatFields are PRML manifest fields whose value MUST round-trip as float
// even when integer-valued. PyYAML preserves float-ness through its native
// type system; JSON+Go must use the json.Number raw form to preserve "1.0".
//
// Version-aware: v0.1 fixed threshold as float64; v0.2 RFC P-XX relaxes
// threshold to int|float, so integer-valued thresholds render as plain
// integers under v0.2.
var floatFieldsV01 = map[string]bool{"threshold": true}
var floatFieldsV02 = map[string]bool{}

func floatFieldsFor(version string) map[string]bool {
	if version == "prml/0.1" {
		return floatFieldsV01
	}
	return floatFieldsV02
}

// renderNumber takes a json.Number (raw string) and the field name, returning
// the canonical byte representation. For float-typed fields, the output must
// match PyYAML's safe_dump float rendering exactly:
//
//   - integer-valued floats are rendered with at least one decimal place
//     (e.g. `1` → `1.0`)
//   - scientific-notation floats whose mantissa has no decimal place receive
//     a `.0` injection before the exponent (e.g. `1e-06` → `1.0e-06`),
//     matching Python's repr(float) which PyYAML inherits.
//
// JSON marshalled by Python's json.dumps already emits 2-digit zero-padded
// exponents (`1e-06`, not `1e-6`), so no exponent-padding is required for the
// v0.1 conformance vectors. Go's own encoding/json marshal does not pad,
// however, so any input round-tripped through Go's marshaler would fail; the
// canonicalizer expects raw json.Number strings preserved by UseNumber.
func renderNumber(n json.Number, field string, floatFields map[string]bool) string {
	s := string(n)
	if !floatFields[field] {
		return s
	}
	eIdx := strings.IndexAny(s, "eE")
	if eIdx < 0 {
		// No exponent.
		if !strings.Contains(s, ".") {
			return s + ".0"
		}
		return s
	}
	// Has exponent: ensure mantissa has a decimal place.
	mantissa := s[:eIdx]
	exponent := s[eIdx:]
	if !strings.Contains(mantissa, ".") {
		return mantissa + ".0" + exponent
	}
	return s
}

// renderScalar emits the canonical form of a non-collection value.
// `field` is the parent key name (for hint-driven float rendering).
func renderScalar(v interface{}, field string, floatFields map[string]bool) (string, error) {
	switch x := v.(type) {
	case nil:
		return "null", nil
	case bool:
		if x {
			return "true", nil
		}
		return "false", nil
	case json.Number:
		return renderNumber(x, field, floatFields), nil
	case string:
		if needsQuoting(x) {
			return quoteSingle(x), nil
		}
		return x, nil
	default:
		return "", fmt.Errorf("renderScalar: unsupported type %T", v)
	}
}

// renderMapping emits a YAML block-style mapping with keys sorted
// lexicographically. Indent is the current depth in spaces.
// Returns the rendered text (without trailing newline at top level).
func renderMapping(m map[string]interface{}, indent int, floatFields map[string]bool) (string, error) {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	pad := strings.Repeat(" ", indent)
	var lines []string
	for _, k := range keys {
		v := m[k]
		switch sub := v.(type) {
		case map[string]interface{}:
			lines = append(lines, fmt.Sprintf("%s%s:", pad, k))
			nested, err := renderMapping(sub, indent+2, floatFields)
			if err != nil {
				return "", err
			}
			lines = append(lines, nested)
		case []interface{}:
			lines = append(lines, fmt.Sprintf("%s%s:", pad, k))
			for _, item := range sub {
				if itemMap, ok := item.(map[string]interface{}); ok {
					nested, err := renderMapping(itemMap, indent+2, floatFields)
					if err != nil {
						return "", err
					}
					padNested := strings.Repeat(" ", indent+2)
					nestedLines := strings.Split(nested, "\n")
					nestedLines[0] = fmt.Sprintf("%s- %s", pad, strings.TrimPrefix(nestedLines[0], padNested))
					lines = append(lines, strings.Join(nestedLines, "\n"))
				} else {
					rendered, err := renderScalar(item, k, floatFields)
					if err != nil {
						return "", err
					}
					lines = append(lines, fmt.Sprintf("%s- %s", pad, rendered))
				}
			}
		default:
			rendered, err := renderScalar(v, k, floatFields)
			if err != nil {
				return "", err
			}
			lines = append(lines, fmt.Sprintf("%s%s: %s", pad, k, rendered))
		}
	}
	return strings.Join(lines, "\n"), nil
}

// Canonicalize emits the canonical byte sequence for a PRML manifest.
// The argument must be a map[string]interface{} as produced by
// json.Decoder with UseNumber enabled.
func Canonicalize(m map[string]interface{}) (string, error) {
	version, _ := m["version"].(string)
	floatFields := floatFieldsFor(version)
	body, err := renderMapping(m, 0, floatFields)
	if err != nil {
		return "", err
	}
	return body + "\n", nil
}

// ManifestHash computes the canonical SHA-256 of a manifest.
func ManifestHash(m map[string]interface{}) (string, error) {
	canonical, err := Canonicalize(m)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256([]byte(canonical))
	return hex.EncodeToString(sum[:]), nil
}

// ─────────────────────────────────────────────────────────────────────────
// Test-vector runner
// ─────────────────────────────────────────────────────────────────────────

type testVector struct {
	ID          string                 `json:"id"`
	Title       string                 `json:"title"`
	Description string                 `json:"description"`
	Input       map[string]interface{} `json:"input"`
	Canonical   string                 `json:"canonical"`
	Hash        string                 `json:"hash"`
}

func loadVectors(path string) ([]testVector, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read %s: %w", path, err)
	}
	dec := json.NewDecoder(strings.NewReader(string(data)))
	dec.UseNumber()
	var vectors []testVector
	if err := dec.Decode(&vectors); err != nil {
		return nil, fmt.Errorf("decode: %w", err)
	}
	return vectors, nil
}

// In test vectors, the `input` is parsed first as map[string]interface{}
// but with UseNumber so we get json.Number for numeric fields.
// Because UseNumber doesn't propagate through nested struct fields, we
// re-parse with a custom approach below.

func runVectors(path string) int {
	data, err := os.ReadFile(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "read %s: %v\n", path, err)
		return 11
	}
	// Parse the entire vectors JSON as []interface{} with UseNumber so
	// nested numeric fields preserve their raw JSON form.
	dec := json.NewDecoder(strings.NewReader(string(data)))
	dec.UseNumber()
	var raw []interface{}
	if err := dec.Decode(&raw); err != nil {
		fmt.Fprintf(os.Stderr, "decode: %v\n", err)
		return 11
	}
	pass, fail := 0, 0
	for _, vRaw := range raw {
		vec, ok := vRaw.(map[string]interface{})
		if !ok {
			fmt.Fprintln(os.Stderr, "vector is not an object")
			fail++
			continue
		}
		id, _ := vec["id"].(string)
		title, _ := vec["title"].(string)
		input, ok := vec["input"].(map[string]interface{})
		if !ok {
			fmt.Fprintf(os.Stderr, "vector %s: input is not an object\n", id)
			fail++
			continue
		}
		expectedCanonical, _ := vec["canonical"].(string)
		expectedHash, _ := vec["hash"].(string)

		produced, err := Canonicalize(input)
		if err != nil {
			fmt.Printf("FAIL  %s  %s  (canonicalize error: %v)\n", id, title, err)
			fail++
			continue
		}
		producedHash := computeSHA256(produced)
		if produced == expectedCanonical && producedHash == expectedHash {
			fmt.Printf("PASS  %s  %s\n", id, title)
			pass++
		} else {
			fmt.Printf("FAIL  %s  %s\n", id, title)
			diffPos := firstDiff(expectedCanonical, produced)
			if diffPos >= 0 {
				lo := max0(diffPos - 10)
				hiE := minN(len(expectedCanonical), diffPos+30)
				hiP := minN(len(produced), diffPos+30)
				fmt.Printf("        first diff @ char %d\n", diffPos)
				fmt.Printf("        expected: %q\n", expectedCanonical[lo:hiE])
				fmt.Printf("        produced: %q\n", produced[lo:hiP])
			}
			if producedHash != expectedHash {
				fmt.Printf("        expected hash: %s\n", expectedHash)
				fmt.Printf("        produced hash: %s\n", producedHash)
			}
			fail++
		}
	}
	fmt.Printf("\nResult: %d/%d vectors passed.\n", pass, pass+fail)
	if fail > 0 {
		return 10
	}
	return 0
}

func computeSHA256(s string) string {
	sum := sha256.Sum256([]byte(s))
	return hex.EncodeToString(sum[:])
}

func firstDiff(a, b string) int {
	n := len(a)
	if len(b) < n {
		n = len(b)
	}
	for i := 0; i < n; i++ {
		if a[i] != b[i] {
			return i
		}
	}
	if len(a) != len(b) {
		return n
	}
	return -1
}

func max0(x int) int {
	if x < 0 {
		return 0
	}
	return x
}

func minN(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// ─────────────────────────────────────────────────────────────────────────
// Verifier
// ─────────────────────────────────────────────────────────────────────────

const (
	exitPass     = 0
	exitBad      = 2 // bad input / spec: unreadable, unparseable, invalid manifest, bad --observed
	exitTampered = 3
	exitFail     = 10
	exitGuard    = 11 // environmental guard: missing sidecar
)

func evaluatePredicate(observed, threshold float64, comparator string) (bool, error) {
	switch comparator {
	case ">=":
		return observed >= threshold, nil
	case "<=":
		return observed <= threshold, nil
	case ">":
		return observed > threshold, nil
	case "<":
		return observed < threshold, nil
	case "==":
		return observed == threshold, nil
	default:
		return false, fmt.Errorf("invalid comparator: %s", comparator)
	}
}

// forbiddenChars: control / non-portable chars disallowed in any PRML string
// field — C0 (U+0000–U+001F), DEL + C1 (U+007F–U+009F), line/paragraph
// separators (U+2028/U+2029), and BOM (U+FEFF). They canonicalise inconsistently
// across YAML engines, so a manifest carrying them is non-portable. Rejecting is
// additive — no conformance vector contains them. Mirrors the Python reference.
var forbiddenChars = regexp.MustCompile("[\\x00-\\x1f\\x7f-\\x9f\\x{2028}\\x{2029}\\x{feff}]")

// forbiddenCharFields walks a decoded manifest and returns the dotted paths of
// any string field (key or value) containing a forbidden char.
func forbiddenCharFields(v interface{}, path string) []string {
	var out []string
	switch t := v.(type) {
	case string:
		if forbiddenChars.MatchString(t) {
			if path == "" {
				path = "(value)"
			}
			out = append(out, path)
		}
	case map[string]interface{}:
		for k, vv := range t {
			child := k
			if path != "" {
				child = path + "." + k
			}
			// A forbidden char in a KEY canonicalizes non-portably just as in a value.
			if forbiddenChars.MatchString(k) {
				out = append(out, child+" (key)")
			}
			out = append(out, forbiddenCharFields(vv, child)...)
		}
	case []interface{}:
		for i, vv := range t {
			out = append(out, forbiddenCharFields(vv, fmt.Sprintf("%s[%d]", path, i))...)
		}
	}
	return out
}

var hex64 = regexp.MustCompile("^[0-9a-f]{64}$")
var uuidv7Re = regexp.MustCompile(`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-7[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$`)
var rfc3339Re = regexp.MustCompile(`^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$`)
var hexAny64 = regexp.MustCompile(`^[0-9a-fA-F]{64}$`)
var topLevelKeys = map[string]bool{
	"version": true, "claim_id": true, "created_at": true, "metric": true,
	"comparator": true, "threshold": true, "dataset": true, "seed": true,
	"producer": true, "model": true, "compute_envelope": true,
	"prior_hash": true, "notes": true, "metric_args": true,
}

var validComparators = map[string]bool{">=": true, "<=": true, ">": true, "<": true, "==": true}

// validateManifest mirrors the Python reference's validate_manifest: it returns
// the list of reasons a manifest is not a valid PRML v0.1/v0.2 manifest (empty =
// valid). Required fields, version, threshold type, comparator, dataset id/hash
// (64 lowercase hex), producer id, and the control / non-portable character rule.
func validateManifest(m map[string]interface{}) []string {
	var errs []string
	for _, f := range []string{"version", "claim_id", "created_at", "metric",
		"comparator", "threshold", "dataset", "seed", "producer"} {
		if _, ok := m[f]; !ok {
			errs = append(errs, "missing required field: "+f)
		}
	}
	if v, _ := m["version"].(string); v != "prml/0.1" && v != "prml/0.2" {
		errs = append(errs, fmt.Sprintf("version must be \"prml/0.1\" or \"prml/0.2\", got \"%v\"", m["version"]))
	}
	if _, ok := m["threshold"].(json.Number); !ok {
		errs = append(errs, "threshold must be a finite number")
	}
	if c, ok := m["comparator"].(string); ok && c != "" && !validComparators[c] {
		errs = append(errs, "comparator must be one of <, <=, ==, >, >=")
	}
	if ds, ok := m["dataset"].(map[string]interface{}); ok {
		for _, f := range []string{"id", "hash"} {
			if _, ok := ds[f]; !ok {
				errs = append(errs, "missing required field: dataset."+f)
			}
		}
		if h, ok := ds["hash"].(string); ok && h != "" && !hex64.MatchString(h) {
			errs = append(errs, "dataset.hash must be 64 lowercase hex chars")
		}
	}
	if prod, ok := m["producer"].(map[string]interface{}); ok {
		if _, ok := prod["id"]; !ok {
			errs = append(errs, "missing required field: producer.id")
		}
	}
	for _, fld := range forbiddenCharFields(m, "") {
		errs = append(errs, fld+": contains a control / non-portable character "+
			"(C0/C1, U+007F, U+2028/U+2029, or U+FEFF) — not allowed in a PRML string field")
	}
	errs = append(errs, schemaConformanceErrors(m)...)
	return errs
}

// Full published-schema conformance (spec/schema/prml-v0.1.schema.json).
// Added in v0.3.12: validators must agree with the published JSON Schema
// (Andes interoperability assessment, finding 1).
func schemaConformanceErrors(m map[string]interface{}) []string {
	var errs []string
	if cid, ok := m["claim_id"].(string); ok && !uuidv7Re.MatchString(cid) {
		errs = append(errs, "claim_id must be a UUIDv7 (schema pattern: version nibble 7, variant 8/9/a/b)")
	}
	if ca, ok := m["created_at"].(string); ok && !rfc3339Re.MatchString(ca) {
		errs = append(errs, "created_at must be an RFC 3339 date-time")
	}
	if met, ok := m["metric"].(string); ok && (len(met) < 1 || len(met) > 256) {
		errs = append(errs, "metric must be 1..256 characters")
	}
	if seed, present := m["seed"]; present && seed != nil {
		if n, ok := seed.(json.Number); !ok {
			errs = append(errs, "seed must be an integer or null")
		} else if _, err := n.Int64(); err != nil {
			// arbitrary-precision uint64 seeds still parse via big int path in hashing;
			// accept anything without a decimal point / exponent
			sTok := n.String()
			if strings.ContainsAny(sTok, ".eE") {
				errs = append(errs, "seed must be an integer or null")
			}
		}
	}
	if ds, ok := m["dataset"].(map[string]interface{}); ok {
		if id, ok := ds["id"].(string); ok && len(id) < 1 {
			errs = append(errs, "dataset.id must be non-empty")
		}
		for k := range ds {
			if k != "id" && k != "hash" && k != "uri" {
				errs = append(errs, "dataset."+k+": unknown field (schema additionalProperties: false)")
			}
		}
	}
	if prod, ok := m["producer"].(map[string]interface{}); ok {
		if id, ok := prod["id"].(string); ok && len(id) < 1 {
			errs = append(errs, "producer.id must be non-empty")
		}
		for k := range prod {
			if k != "id" && k != "signature" {
				errs = append(errs, "producer."+k+": unknown field (schema additionalProperties: false)")
			}
		}
	}
	if ph, present := m["prior_hash"]; present {
		if s, ok := ph.(string); !ok || !hexAny64.MatchString(s) {
			errs = append(errs, "prior_hash must be 64 hex characters")
		}
	}
	if nt, present := m["notes"]; present {
		if s, ok := nt.(string); !ok || len([]rune(s)) > 4096 {
			errs = append(errs, "notes must be a string of at most 4096 characters")
		}
	}
	for k := range m {
		if !topLevelKeys[k] {
			errs = append(errs, k+": unknown top-level field (schema additionalProperties: false)")
		}
	}
	return errs
}

func cmdHash(specPath string) int {
	data, err := os.ReadFile(specPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "hash: %v\n", err)
		return exitBad
	}
	dec := json.NewDecoder(strings.NewReader(string(data)))
	dec.UseNumber()
	var m map[string]interface{}
	if err := dec.Decode(&m); err != nil {
		fmt.Fprintf(os.Stderr, "hash: parse: %v\n", err)
		return exitBad
	}
	if errs := validateManifest(m); len(errs) > 0 {
		fmt.Fprintln(os.Stderr, "hash: invalid manifest:")
		for _, e := range errs {
			fmt.Fprintf(os.Stderr, "  - %s\n", e)
		}
		return exitBad
	}
	h, err := ManifestHash(m)
	if err != nil {
		fmt.Fprintf(os.Stderr, "hash: %v\n", err)
		return exitBad
	}
	fmt.Println(h)
	return exitPass
}

func cmdVerify(specPath, observedStr string) int {
	data, err := os.ReadFile(specPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "verify: %v\n", err)
		return exitBad
	}
	dec := json.NewDecoder(strings.NewReader(string(data)))
	dec.UseNumber()
	var m map[string]interface{}
	if err := dec.Decode(&m); err != nil {
		fmt.Fprintf(os.Stderr, "verify: parse: %v\n", err)
		return exitBad
	}
	if errs := validateManifest(m); len(errs) > 0 {
		fmt.Fprintln(os.Stderr, "verify: invalid manifest:")
		for _, e := range errs {
			fmt.Fprintf(os.Stderr, "  - %s\n", e)
		}
		return exitBad
	}
	canonical, err := Canonicalize(m)
	if err != nil {
		fmt.Fprintf(os.Stderr, "verify: %v\n", err)
		return exitBad
	}
	computed := computeSHA256(canonical)
	sidecar := strings.TrimSuffix(specPath, getExt(specPath)) + ".prml.sha256"
	sidecarBytes, err := os.ReadFile(sidecar)
	if err != nil {
		fmt.Fprintf(os.Stderr, "verify: sidecar not found: %s\n", sidecar)
		return exitGuard
	}
	claimed := strings.TrimSpace(string(sidecarBytes))
	if computed != claimed {
		fmt.Println("TAMPERED")
		fmt.Printf("  recorded:    %s\n", claimed)
		fmt.Printf("  recomputed:  %s\n", computed)
		return exitTampered
	}
	if observedStr == "" {
		fmt.Printf("hash OK: %s\n", computed)
		fmt.Println("(no --observed value given; predicate not evaluated)")
		return exitPass
	}
	observed, err := strconv.ParseFloat(observedStr, 64)
	if err != nil {
		fmt.Fprintf(os.Stderr, "verify: --observed must be a finite number: %v\n", err)
		return exitBad
	}
	comparator, _ := m["comparator"].(string)
	thresholdRaw, _ := m["threshold"].(json.Number)
	threshold, err := thresholdRaw.Float64()
	if err != nil {
		fmt.Fprintf(os.Stderr, "verify: threshold not numeric: %v\n", err)
		return exitBad
	}
	metric, _ := m["metric"].(string)
	ok, err := evaluatePredicate(observed, threshold, comparator)
	if err != nil {
		fmt.Fprintf(os.Stderr, "verify: %v\n", err)
		return exitBad
	}
	if ok {
		fmt.Printf("PASS  metric=%s  observed=%g  %s  threshold=%g\n",
			metric, observed, comparator, threshold)
		return exitPass
	}
	fmt.Printf("FAIL  metric=%s  observed=%g  NOT %s  threshold=%g\n",
		metric, observed, comparator, threshold)
	return exitFail
}

func getExt(p string) string {
	for i := len(p) - 1; i >= 0; i-- {
		if p[i] == '.' {
			return p[i:]
		}
		if p[i] == '/' {
			break
		}
	}
	return ""
}

// ─────────────────────────────────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────────────────────────────────

func usage() int {
	fmt.Fprintln(os.Stderr, `falsify-go — PRML v0.1 third reference implementation (Go)

Commands:
  test-vectors <vectors.json>            run conformance suite
  hash <spec.json>                       print canonical SHA-256
  verify <spec.json> [--observed <v>]    verify hash; if --observed, evaluate

Exit codes: 0=PASS, 2=BAD (bad input/spec), 3=TAMPERED, 10=FAIL, 11=GUARD (missing sidecar)
Spec:    https://spec.falsify.dev/v0.1`)
	return exitGuard
}

func main() {
	args := os.Args[1:]
	if len(args) == 0 {
		os.Exit(usage())
	}
	switch args[0] {
	case "test-vectors":
		if len(args) < 2 {
			os.Exit(usage())
		}
		os.Exit(runVectors(args[1]))
	case "hash":
		if len(args) < 2 {
			os.Exit(usage())
		}
		os.Exit(cmdHash(args[1]))
	case "verify":
		if len(args) < 2 {
			os.Exit(usage())
		}
		observed := ""
		for i, a := range args {
			if a == "--observed" && i+1 < len(args) {
				observed = args[i+1]
			}
		}
		os.Exit(cmdVerify(args[1], observed))
	case "-h", "--help":
		usage()
		os.Exit(0)
	default:
		os.Exit(usage())
	}
}
