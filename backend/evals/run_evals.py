#!/usr/bin/env python3
"""
Eval harness for data-analyst-agent.
Runs golden dataset queries and scores them.
Usage: python backend/evals/run_evals.py
"""

import sys
import json
import time
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from agent import run_graph
from tools import get_dataset_info

# ── Load dataset ──────────────────────────────────────────────────────────────
DATASET_PATH = os.path.join(os.path.dirname(__file__), '../../sample_data.csv')
df = pd.read_csv(DATASET_PATH)
dataset_json = df.to_json()
dataset_info = get_dataset_info(df)

# ── Load golden dataset ───────────────────────────────────────────────────────
GOLDEN_PATH = os.path.join(os.path.dirname(__file__), 'golden_dataset.json')
with open(GOLDEN_PATH) as f:
    golden = json.load(f)


def run_query(query: str) -> dict:
    """Run a single query and return the results."""
    results = {"insights": "", "output": "", "error": None}
    try:
        for event in run_graph(query, dataset_json, dataset_info, df):
            if event.get("type") == "node_done":
                if event.get("node") == "interpreter":
                    results["insights"] = event.get("insights", "")
                if event.get("node") == "executor":
                    results["output"] = event.get("output", "")
            if event.get("type") == "error":
                results["error"] = event.get("message", "unknown error")
                break
            if event.get("type") == "done":
                break
    except Exception as e:
        results["error"] = str(e)
    return results


def score_result(case: dict, result: dict) -> dict:
    """Score a single eval case."""
    score = {"id": case["id"], "query": case["query"], "difficulty": case["difficulty"]}

    if result.get("error"):
        score["passed"] = False
        score["reason"] = f"Error: {result['error']}"
        score["score"] = 0.0
        return score

    # Combine insights and output for checking
    full_text = (result["insights"] + " " + result["output"]).lower()

    # Check expected_contains
    missing = []
    for term in case.get("expected_contains", []):
        # Any one of the terms in a group is enough (OR logic within groups)
        if isinstance(term, list):
            if not any(t.lower() in full_text for t in term):
                missing.append(str(term))
        else:
            if term.lower() not in full_text:
                missing.append(term)

    # Check expected_not_contains
    bad_found = []
    for term in case.get("expected_not_contains", []):
        if term.lower() in full_text:
            bad_found.append(term)

    if not missing and not bad_found:
        score["passed"] = True
        score["score"] = 1.0
        score["reason"] = "All checks passed"
    else:
        score["passed"] = False
        score["score"] = 0.0
        reasons = []
        if missing:
            reasons.append(f"Missing: {missing}")
        if bad_found:
            reasons.append(f"Should not contain: {bad_found}")
        score["reason"] = " | ".join(reasons)

    return score


def run_all_evals():
    """Run all eval cases and print results."""
    print(f"\n{'='*60}")
    print(f"  data-analyst-agent eval harness")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    scores = []
    passed = 0
    total = len(golden)

    for i, case in enumerate(golden, 1):
        print(f"[{i}/{total}] {case['id']} ({case['difficulty']}) — {case['query'][:60]}...")
        start = time.time()
        result = run_query(case["query"])
        elapsed = time.time() - start
        score = score_result(case, result)
        scores.append(score)

        status = "✓ PASS" if score["passed"] else "✗ FAIL"
        print(f"         {status} ({elapsed:.1f}s) — {score['reason']}\n")

        if score["passed"]:
            passed += 1

        # Small delay to avoid rate limiting
        time.sleep(12)

    # ── Summary ───────────────────────────────────────────────────────────────
    pass_rate = passed / total * 100
    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed}/{total} passed ({pass_rate:.1f}%)")
    print(f"{'='*60}")

    # By difficulty
    for diff in ["easy", "medium", "hard"]:
        diff_cases = [s for s in scores if s["difficulty"] == diff]
        if diff_cases:
            diff_passed = sum(1 for s in diff_cases if s["passed"])
            print(f"  {diff.upper()}: {diff_passed}/{len(diff_cases)}")

    print(f"{'='*60}\n")

    # ── Save results ──────────────────────────────────────────────────────────
    results_path = os.path.join(os.path.dirname(__file__), 'last_results.json')
    with open(results_path, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "pass_rate": pass_rate,
            "passed": passed,
            "total": total,
            "scores": scores,
        }, f, indent=2)
    print(f"Results saved to {results_path}")

    # ── CI gate ───────────────────────────────────────────────────────────────
    # If all failures are rate limit errors, skip CI gate
    rate_limit_failures = sum(1 for s in scores if not s["passed"] and "rate limit" in s.get("reason", "").lower())
    if rate_limit_failures == total - passed:
        print(f"\n⚠️  CI SKIPPED: all failures due to rate limits — not a regression")
        sys.exit(0)

    MIN_PASS_RATE = 70.0
    if pass_rate < MIN_PASS_RATE:
        print(f"\n❌ CI GATE FAILED: pass rate {pass_rate:.1f}% < {MIN_PASS_RATE}% minimum")
        sys.exit(1)
    else:
        print(f"\n✅ CI GATE PASSED: pass rate {pass_rate:.1f}% >= {MIN_PASS_RATE}% minimum")
        sys.exit(0)


if __name__ == "__main__":
    run_all_evals()
