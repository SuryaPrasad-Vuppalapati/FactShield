#!/usr/bin/env python3
"""
Comprehensive test script for all 8 FactShield blueprint features.
Tests both local and online scenarios with response structure validation.
"""
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Tuple

BASE_URL = "http://127.0.0.1:8000/api/v1"
DOC_ID = "ecf26db3-d71d-401c-ab41-c8feb1277464"  # d2l-en.pdf

# Test configurations: (endpoint, mode_label, query_local, query_online)
TESTS = [
    # Student endpoints
    ("student/concept-guide", "concept-guide",
     "What is deep learning? Explain from the d2l-en.pdf",
     "What were the major AI safety conference highlights in 2026?"),

    ("student/problem-navigator", "problem-navigator",
     "How do I solve a neural network problem?",
     "What are the latest breakthroughs in quantum computing as of 2026?"),

    ("student/submission-validator", "submission-validator",
     "Check if my solution is correct. I used backpropagation.",
     "Validate: What are the current state-of-the-art LLM capabilities in 2026?"),

    ("student/exam-simulator", "exam-simulator",
     "Generate an exam question about optimization methods",
     "Create exam questions about 2026 AI trends"),

    # Teacher endpoints
    ("teacher/assignment-grader", "assignment-grader",
     "Grade this student submission on deep learning",
     "Grade a student response about 2026 AI developments"),

    ("teacher/exam-generator", "exam-generator",
     "Generate exam questions from d2l-en.pdf about neural networks",
     "Generate exam questions about 2026 AI safety issues"),

    ("teacher/adaptive-feedback", "adaptive-feedback",
     "Provide feedback on deep learning understanding",
     "Provide adaptive feedback on 2026 AI landscape knowledge"),

    ("teacher/learning-insights", "learning-insights",
     "Analyze learning patterns from deep learning topics",
     "Analyze learning insights about 2026 AI trends"),
]

REQUIRED_FIELDS = {
    "text", "entailment", "consistency", "confidence",
    "fallback_type", "source_used", "source_reference"
}


def test_endpoint(endpoint: str, query: str, scenario: str) -> Tuple[bool, Dict[str, Any]]:
    """Test a single endpoint with a query.

    Returns: (success, result_dict)
    """
    url = f"{BASE_URL}/{endpoint}"
    payload = {
        "question": query,
        "doc_ids": [DOC_ID],
        "chat_history": []
    }

    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode('utf-8')

    start_time = time.time()

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=45) as response:
            elapsed = time.time() - start_time
            response_data = json.loads(response.read().decode('utf-8'))

            # Validate response structure
            missing_fields = REQUIRED_FIELDS - set(response_data.keys())
            has_citation = "**Source:" in response_data.get("text", "") or \
                "Reference:" in response_data.get("text", "")

            return True, {
                "status": "success",
                "endpoint": endpoint,
                "scenario": scenario,
                "latency_sec": round(elapsed, 2),
                "http_status": response.status,
                "response": response_data,
                "validation": {
                    "all_fields_present": len(missing_fields) == 0,
                    "missing_fields": list(missing_fields),
                    "has_citation": has_citation,
                    "text_length": len(response_data.get("text", "")),
                }
            }

    except urllib.error.HTTPError as e:
        elapsed = time.time() - start_time
        return False, {
            "status": "http_error",
            "endpoint": endpoint,
            "scenario": scenario,
            "latency_sec": round(elapsed, 2),
            "http_status": e.code,
            "error": str(e)
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return False, {
            "status": "error",
            "endpoint": endpoint,
            "scenario": scenario,
            "latency_sec": round(elapsed, 2),
            "error": str(e)
        }


def print_result(result: Dict[str, Any]) -> None:
    """Pretty print a test result."""
    endpoint = result.get("endpoint", "unknown")
    scenario = result.get("scenario", "unknown")
    status = result.get("status", "unknown")
    latency = result.get("latency_sec", "N/A")

    if status == "success":
        validation = result.get("validation", {})
        all_fields = validation.get("all_fields_present", False)
        has_citation = validation.get("has_citation", False)
        text_len = validation.get("text_length", 0)

        fields_status = "✓" if all_fields else "✗"
        citation_status = "✓" if has_citation else "✗"

        print(f"\n  [{endpoint}] {scenario}")
        print(f"    Status: ✓ SUCCESS ({latency}s)")
        print(f"    Fields: {fields_status} {all_fields}")
        if not all_fields:
            missing = validation.get("missing_fields", [])
            print(f"      Missing: {missing}")
        print(f"    Citation: {citation_status} {has_citation}")
        print(f"    Response length: {text_len} chars")

    else:
        print(f"\n  [{endpoint}] {scenario}")
        print(f"    Status: ✗ FAILED ({latency}s)")
        print(f"    Error: {result.get('error', result.get('http_status', 'Unknown'))}")


def main():
    """Run all feature tests."""
    print("\n" + "=" * 70)
    print("FactShield Feature Validation Test Suite")
    print("=" * 70)
    print(f"\nTesting {len(TESTS)} features × 2 scenarios = {len(TESTS) * 2} total tests")
    print("Scenarios: [1] Local query (from d2l-en.pdf)")
    print("           [2] Online query (external sources)\n")

    results = []
    passed = 0
    failed = 0

    for endpoint, mode, query_local, query_online in TESTS:
        print(f"\nTesting: {endpoint}")

        # Test 1: Local scenario
        print("  [Scenario 1/2] Local query...")
        success, result = test_endpoint(endpoint, query_local, "local")
        results.append(result)
        print_result(result)
        if success and result.get("validation", {}).get("all_fields_present"):
            passed += 1
        else:
            failed += 1

        time.sleep(0.5)  # Small delay between requests

        # Test 2: Online scenario
        print("  [Scenario 2/2] Online query...")
        success, result = test_endpoint(endpoint, query_online, "online")
        results.append(result)
        print_result(result)
        if success and result.get("validation", {}).get("all_fields_present"):
            passed += 1
        else:
            failed += 1

        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total tests: {len(results)}")
    print(f"Passed (valid structure): {passed}")
    print(f"Failed: {failed}")
    print(f"Pass rate: {(passed / len(results) * 100):.1f}%")

    # Latency analysis
    latencies = [r.get("latency_sec", 0) for r in results if r.get("status") == "success"]
    if latencies:
        print("\nLatency Analysis:")
        print(f"  Min: {min(latencies):.2f}s")
        print(f"  Max: {max(latencies):.2f}s")
        print(f"  Avg: {sum(latencies) / len(latencies):.2f}s")

    print("\n" + "=" * 70)

    # Save detailed results
    with open("/tmp/factshield_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nDetailed results saved to: /tmp/factshield_test_results.json")


if __name__ == "__main__":
    main()
