package main

// prml-linkage/0 — Go reference implementation (draft).
//
// Spec: spec/linkage/prml-linkage-0.md. Byte-parity with the Python and
// JavaScript references is asserted by tests/test_linkage_parity.py via
// the `linkage-parity` subcommand (stdin/stdout JSON protocol).

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"regexp"
	"sort"
	"time"
)

const linkageVersion = "prml-linkage/0"

var linkageStartFields = []string{"linkage_version", "manifest_hash", "receipt", "run"}
var linkageFinalFields = []string{"linkage_version", "manifest_hash", "receipt", "run", "start_hash", "result"}
var linkageRunFields = []string{"dataset_hash", "environment", "id", "model_version", "started_at"}
var linkageResultFields = []string{"digest", "exit_code", "finished_at", "observed"}
var linkageValidExitCodes = map[int]bool{0: true, 3: true, 10: true, 11: true}

var sha256Re = regexp.MustCompile(`^[0-9a-f]{64}$`)

type linkageFailure struct {
	Check  string `json:"check"`
	Detail string `json:"detail"`
}

type linkageReport struct {
	OK       bool             `json:"ok"`
	Tier     interface{}      `json:"tier"`
	Failures []linkageFailure `json:"failures"`
	Skipped  []string         `json:"skipped"`
}

func linkageHash(record map[string]interface{}) (string, error) {
	canonical, err := Canonicalize(record)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256([]byte(canonical))
	return hex.EncodeToString(sum[:]), nil
}

func parseRFC3339(v interface{}) (time.Time, error) {
	s, ok := v.(string)
	if !ok {
		return time.Time{}, fmt.Errorf("timestamp is not a string")
	}
	return time.Parse(time.RFC3339, s)
}

func sortedFieldNames(m map[string]interface{}) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

func sameFieldSet(m map[string]interface{}, expected []string) bool {
	if len(m) != len(expected) {
		return false
	}
	got := sortedFieldNames(m)
	exp := append([]string(nil), expected...)
	sort.Strings(exp)
	for i := range got {
		if got[i] != exp[i] {
			return false
		}
	}
	return true
}

func exitCodeOf(v interface{}) (int, bool) {
	switch x := v.(type) {
	case json.Number:
		i, err := x.Int64()
		if err != nil {
			return 0, false
		}
		return int(i), true
	case float64:
		return int(x), true
	}
	return 0, false
}

func linkageValidateShape(record map[string]interface{}, final bool) []string {
	var problems []string
	expected := linkageStartFields
	if final {
		expected = linkageFinalFields
	}
	if lv, _ := record["linkage_version"].(string); lv != linkageVersion {
		problems = append(problems, fmt.Sprintf("linkage_version must be %q", linkageVersion))
	}
	expSet := map[string]bool{}
	for _, k := range expected {
		expSet[k] = true
	}
	var missing, extra []string
	for _, k := range expected {
		if _, ok := record[k]; !ok {
			missing = append(missing, k)
		}
	}
	for k := range record {
		if !expSet[k] {
			extra = append(extra, k)
		}
	}
	sort.Strings(missing)
	sort.Strings(extra)
	if len(missing) > 0 {
		problems = append(problems, fmt.Sprintf("missing fields: %v", missing))
	}
	if len(extra) > 0 {
		problems = append(problems, fmt.Sprintf("unknown fields: %v", extra))
	}
	run, ok := record["run"].(map[string]interface{})
	if !ok {
		problems = append(problems, "run is not a mapping")
	} else {
		if !sameFieldSet(run, linkageRunFields) {
			problems = append(problems, fmt.Sprintf("run fields must be exactly %v", linkageRunFields))
		}
		if dh, _ := run["dataset_hash"].(string); !sha256Re.MatchString(dh) {
			problems = append(problems, "run.dataset_hash must be 64 lowercase hex chars")
		}
		if _, err := parseRFC3339(run["started_at"]); err != nil {
			problems = append(problems, "run.started_at is not RFC 3339")
		}
	}
	if mh, _ := record["manifest_hash"].(string); !sha256Re.MatchString(mh) {
		problems = append(problems, "manifest_hash must be 64 lowercase hex chars")
	}
	if final {
		if sh, _ := record["start_hash"].(string); !sha256Re.MatchString(sh) {
			problems = append(problems, "start_hash must be 64 lowercase hex chars")
		}
		result, ok := record["result"].(map[string]interface{})
		if !ok {
			problems = append(problems, "result is not a mapping")
		} else {
			if !sameFieldSet(result, linkageResultFields) {
				problems = append(problems, fmt.Sprintf("result fields must be exactly %v", linkageResultFields))
			}
			if ec, ok := exitCodeOf(result["exit_code"]); !ok || !linkageValidExitCodes[ec] {
				problems = append(problems, "result.exit_code must be one of 0,3,10,11")
			}
			if dg, _ := result["digest"].(string); !sha256Re.MatchString(dg) {
				problems = append(problems, "result.digest must be 64 lowercase hex chars")
			}
			if _, err := parseRFC3339(result["finished_at"]); err != nil {
				problems = append(problems, "result.finished_at is not RFC 3339")
			}
		}
	}
	return problems
}

// linkageFinalize builds the final record from a start record plus results.
// observed stays a json.Number; the canonicalizer's linkage float rule
// renders it as float64 ("x.0" for integer values).
func linkageFinalize(start map[string]interface{}, observed json.Number, digest string, exitCode int, finishedAt string) (map[string]interface{}, error) {
	if problems := linkageValidateShape(start, false); len(problems) > 0 {
		return nil, fmt.Errorf("invalid start record: %v", problems)
	}
	if !linkageValidExitCodes[exitCode] {
		return nil, fmt.Errorf("exit_code must be one of 0,3,10,11")
	}
	if !sha256Re.MatchString(digest) {
		return nil, fmt.Errorf("result digest must be 64 lowercase hex chars")
	}
	if _, err := parseRFC3339(finishedAt); err != nil {
		return nil, fmt.Errorf("finished_at is not RFC 3339: %w", err)
	}
	startHash, err := linkageHash(start)
	if err != nil {
		return nil, err
	}
	runCopy := map[string]interface{}{}
	for k, v := range start["run"].(map[string]interface{}) {
		runCopy[k] = v
	}
	return map[string]interface{}{
		"linkage_version": start["linkage_version"],
		"manifest_hash":   start["manifest_hash"],
		"receipt":         start["receipt"],
		"run":             runCopy,
		"start_hash":      startHash,
		"result": map[string]interface{}{
			"observed":    observed,
			"digest":      digest,
			"exit_code":   json.Number(fmt.Sprintf("%d", exitCode)),
			"finished_at": finishedAt,
		},
	}, nil
}

func numberValue(v interface{}) (float64, bool) {
	switch x := v.(type) {
	case json.Number:
		f, err := x.Float64()
		if err != nil {
			return 0, false
		}
		return f, true
	case float64:
		return x, true
	}
	return 0, false
}

func linkageVerify(final map[string]interface{}, start map[string]interface{}, manifest map[string]interface{}) linkageReport {
	report := linkageReport{Failures: []linkageFailure{}, Skipped: []string{}}

	if problems := linkageValidateShape(final, true); len(problems) > 0 {
		for _, p := range problems {
			report.Failures = append(report.Failures, linkageFailure{"malformed", p})
		}
		report.Tier = nil
		return report
	}

	tier := "L1"
	if start != nil {
		tier = "L2"
		sh, err := linkageHash(start)
		if err != nil || sh != final["start_hash"].(string) {
			report.Failures = append(report.Failures, linkageFailure{"chain-broken", "hash(start) != start_hash"})
		} else {
			// Reconstruct the start view from the final record and compare bytes.
			view := map[string]interface{}{
				"linkage_version": final["linkage_version"],
				"manifest_hash":   final["manifest_hash"],
				"receipt":         final["receipt"],
				"run":             final["run"],
			}
			ca, errA := Canonicalize(start)
			cb, errB := Canonicalize(view)
			if errA != nil || errB != nil || ca != cb {
				report.Failures = append(report.Failures, linkageFailure{"chain-broken", "start fields differ between start and final"})
			}
		}
	} else {
		report.Skipped = append(report.Skipped, "chain (no start record supplied)")
	}

	run := final["run"].(map[string]interface{})
	result := final["result"].(map[string]interface{})
	started, _ := parseRFC3339(run["started_at"])
	finished, _ := parseRFC3339(result["finished_at"])
	if !started.Before(finished) {
		report.Failures = append(report.Failures, linkageFailure{"chronology", "started_at is not before finished_at"})
	}

	if manifest != nil {
		mh, err := ManifestHash(manifest)
		if err == nil && final["manifest_hash"].(string) != mh {
			report.Failures = append(report.Failures, linkageFailure{"manifest-mismatch", "manifest_hash differs"})
		}
		var mDatasetHash string
		if ds, ok := manifest["dataset"].(map[string]interface{}); ok {
			mDatasetHash, _ = ds["hash"].(string)
		}
		if run["dataset_hash"].(string) != mDatasetHash {
			report.Failures = append(report.Failures, linkageFailure{"dataset-mismatch", "run.dataset_hash != manifest dataset.hash"})
		}
		comparator, _ := manifest["comparator"].(string)
		threshold, thOK := numberValue(manifest["threshold"])
		exitCode, _ := exitCodeOf(result["exit_code"])
		observed, obOK := numberValue(result["observed"])
		if thOK && obOK && (exitCode == 0 || exitCode == 10) {
			var passed, known bool
			switch comparator {
			case ">=":
				passed, known = observed >= threshold, true
			case "<=":
				passed, known = observed <= threshold, true
			case ">":
				passed, known = observed > threshold, true
			case "<":
				passed, known = observed < threshold, true
			case "==":
				passed, known = observed == threshold, true
			}
			if known {
				expected := 10
				if passed {
					expected = 0
				}
				if exitCode != expected {
					report.Failures = append(report.Failures, linkageFailure{
						"verdict-mismatch",
						fmt.Sprintf("observed vs threshold implies exit %d, record says %d", expected, exitCode),
					})
				}
			}
		} else if exitCode == 3 || exitCode == 11 {
			report.Skipped = append(report.Skipped, "verdict recompute (error exit code)")
		}
	} else {
		report.Skipped = append(report.Skipped, "dataset + verdict (no manifest supplied)")
	}

	report.OK = len(report.Failures) == 0
	report.Tier = tier
	return report
}

// cmdLinkageParity implements the cross-language parity protocol:
// one JSON request on stdin, one JSON response on stdout.
func cmdLinkageParity() int {
	data, err := io.ReadAll(os.Stdin)
	if err != nil {
		fmt.Fprintln(os.Stderr, "linkage-parity: read stdin:", err)
		return 2
	}
	var req struct {
		Mode       string                 `json:"mode"`
		Record     map[string]interface{} `json:"record"`
		Start      map[string]interface{} `json:"start"`
		Final      map[string]interface{} `json:"final"`
		Manifest   map[string]interface{} `json:"manifest"`
		Observed   json.Number            `json:"observed"`
		Digest     string                 `json:"digest"`
		ExitCode   int                    `json:"exit_code"`
		FinishedAt string                 `json:"finished_at"`
	}
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.UseNumber()
	if err := dec.Decode(&req); err != nil {
		fmt.Fprintln(os.Stderr, "linkage-parity: bad request:", err)
		return 2
	}
	out := map[string]interface{}{}
	switch req.Mode {
	case "canonical":
		canonical, err := Canonicalize(req.Record)
		if err != nil {
			fmt.Fprintln(os.Stderr, "linkage-parity:", err)
			return 2
		}
		sum := sha256.Sum256([]byte(canonical))
		out["canonical"] = canonical
		out["hash"] = hex.EncodeToString(sum[:])
	case "finalize":
		final, err := linkageFinalize(req.Start, req.Observed, req.Digest, req.ExitCode, req.FinishedAt)
		if err != nil {
			fmt.Fprintln(os.Stderr, "linkage-parity:", err)
			return 2
		}
		h, err := linkageHash(final)
		if err != nil {
			fmt.Fprintln(os.Stderr, "linkage-parity:", err)
			return 2
		}
		out["final"] = final
		out["hash"] = h
	case "verify":
		report := linkageVerify(req.Final, req.Start, req.Manifest)
		enc, _ := json.Marshal(report)
		os.Stdout.Write(enc)
		return 0
	default:
		fmt.Fprintln(os.Stderr, "linkage-parity: unknown mode", req.Mode)
		return 2
	}
	enc, _ := json.Marshal(out)
	os.Stdout.Write(enc)
	return 0
}
