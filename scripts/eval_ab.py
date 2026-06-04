#!/usr/bin/env python3
"""
eval_ab.py — A/B evaluation comparing Groq vs Azure for CX Knowledge Base RAG

Runs the evaluation harness twice with different LLM providers and produces a
side-by-side comparison report. Always restores the original provider at the end.

Usage:
  python3 scripts/eval_ab.py              # Compare Azure (baseline) vs Groq
  python3 scripts/eval_ab.py --providers azure,groq
  python3 scripts/eval_ab.py --dry-run    # Test connectivity only
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from typing import Optional

import requests
from eval_rag import (
    TestCase,
    load_env,
    check_container,
    query_rag,
    evaluate_response,
    build_judge_model,
)


@dataclass
class ProviderResult:
    """Results for one provider."""
    provider: str
    model: str
    responses: list[dict]  # per-question results with scores and latency
    avg_scores: dict[str, float]  # dimension -> avg score


def get_current_provider(base_url: str, api_key: str, workspace: str) -> Optional[dict]:
    """Fetch current workspace settings to identify the active LLM provider."""
    url = f"{base_url}/api/v1/workspace/{workspace}"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return {
            "provider": data.get("workspace", {}).get("llmProvider", "unknown"),
            "model": data.get("workspace", {}).get("llmPreference", "unknown"),
        }
    except Exception as e:
        print(f"✗ Failed to get current provider: {e}")
        return None


def set_provider(
    base_url: str, api_key: str, workspace: str, provider: str, model: str
) -> bool:
    """Switch the LLM provider for the workspace."""
    url = f"{base_url}/api/v1/workspace/{workspace}/update"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    # Build the payload based on provider type
    if provider == "groq":
        payload = {
            "llmProvider": "groq",
            "groqModelPref": model,
        }
    elif provider == "azure":
        payload = {
            "llmProvider": "azure",
            "azureOpenAiModelPref": model,
        }
    else:
        print(f"✗ Unknown provider: {provider}")
        return False

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=5)
        resp.raise_for_status()
        print(f"✓ Switched to {provider} ({model})")
        return True
    except Exception as e:
        print(f"✗ Failed to set provider {provider}: {e}")
        return False


def run_evaluation(
    base_url: str,
    api_key: str,
    workspace: str,
    judge_model,
    test_cases: list[TestCase],
    provider: str,
) -> Optional[ProviderResult]:
    """Run the full evaluation suite for a single provider."""
    print(f"\n[*] Evaluating {provider.upper()} provider ({len(test_cases)} questions)")
    print("-" * 70)

    responses = []

    for i, tc in enumerate(test_cases, 1):
        print(f"\n{i}. {tc.label}")
        print(f"   Q: {tc.question}")

        # Query the RAG system and measure latency
        start_time = time.time()
        rag_result = query_rag(base_url, api_key, workspace, tc.question)
        latency_ms = (time.time() - start_time) * 1000

        if not rag_result:
            print("   ✗ Query failed")
            responses.append({
                "question": tc.label,
                "error": "query_failed",
                "latency_ms": latency_ms,
            })
            continue

        response_text = rag_result.get("textResponse", "")
        if not response_text:
            print("   ✗ No response returned")
            responses.append({
                "question": tc.label,
                "error": "empty_response",
                "latency_ms": latency_ms,
            })
            continue

        # Extract retrieved context from sources
        sources = rag_result.get("sources", [])
        retrieved_context = "\n".join(
            source.get("text", "")[:500] for source in sources
        ) if sources else response_text

        print(f"   A: {response_text[:100]}...")
        print(f"   ⏱ Latency: {latency_ms:.0f}ms")

        # Evaluate on all dimensions
        question_result = {
            "question": tc.label,
            "response": response_text[:200],  # Truncate for storage
            "latency_ms": latency_ms,
            "evaluations": {},
        }

        for eval_type in ["correctness", "groundedness", "helpfulness"]:
            eval_result = evaluate_response(
                response_text,
                tc.question,
                tc.expected_keywords,
                tc.expected_answer,
                retrieved_context,
                judge_model,
                eval_type,
            )
            score = eval_result.get("score", 0.0)
            method = eval_result.get("method", "unknown")

            question_result["evaluations"][eval_type] = {
                "score": score,
                "method": method,
            }

            # Score display
            if score >= 0.7:
                status = "✓"
            elif score >= 0.5:
                status = "~"
            else:
                status = "✗"

            print(f"   {status} {eval_type}: {score:.2f} ({method})")

        responses.append(question_result)

    # Compute averages per dimension
    avg_scores = {}
    for eval_type in ["correctness", "groundedness", "helpfulness"]:
        scores = [
            r["evaluations"][eval_type]["score"]
            for r in responses
            if "evaluations" in r and eval_type in r["evaluations"]
        ]
        if scores:
            avg_scores[eval_type] = sum(scores) / len(scores)

    return ProviderResult(
        provider=provider,
        model="",  # Will be populated from current settings
        responses=responses,
        avg_scores=avg_scores,
    )


def build_test_cases() -> list[TestCase]:
    """Build all 10 test cases from docs/test-questions.md."""
    return [
        # Should answer
        TestCase(
            label="Q1: Why native plant garden?",
            question="Why should I consider a native plant garden?",
            expected_keywords=["native", "biodiversity", "wildlife", "maintenance", "local"],
            expected_answer="biodiversity, wildlife support, low maintenance, local adaptation",
        ),
        TestCase(
            label="Q2: How to choose native plants?",
            question="How should a gardener choose native plants for different conditions in their yard?",
            expected_keywords=["sunlight", "moisture", "soil", "conditions", "native"],
            expected_answer="choose based on sunlight, moisture, soil, and wildlife goals",
        ),
        TestCase(
            label="Q3: Moist, shady backyard plants",
            question="What native plants are recommended for my moist, shady backyard garden?",
            expected_keywords=["shade", "moist", "wet", "salal", "fern", "cedar"],
            expected_answer="salal, ferns, hemlock, redcedar, or other shade-tolerant natives",
        ),
        TestCase(
            label="Q4: Big white flowers — where to plant?",
            question="I like the look of big white flowers in my garden. Which plants would achieve this? Where could I plant them?",
            expected_keywords=["white", "flower", "dogwood", "elderberry", "mock-orange"],
            expected_answer="dogwood, red elderberry, mock-orange for sunny; ninebark or fringecup for shade",
        ),
        TestCase(
            label="Q5: Front yard pollinator shrub",
            question="I need a new shrub in my front yard that would also attract pollinators. What are some options?",
            expected_keywords=["shrub", "front", "sun", "pollinator", "native"],
            expected_answer="oceanspray, mock-orange, currant, rose, or snowberry",
        ),
        # Should NOT answer
        TestCase(
            label="Q6: Pet-safe plants",
            question="Which native plants are safest if I have a pet dog?",
            expected_keywords=["pet", "dog", "safe", "toxicity"],
            expected_answer="acknowledge pet safety is not covered in the documents",
        ),
        TestCase(
            label="Q7: Winter maintenance",
            question="Which native plants require the least maintenance during winter?",
            expected_keywords=["winter", "maintenance", "low"],
            expected_answer="acknowledge winter maintenance is not ranked in the documents",
        ),
        TestCase(
            label="Q8: Lawn reseeding timing",
            question="What is the best time of year to resod my lawn?",
            expected_keywords=["lawn", "resod", "grass", "manicured"],
            expected_answer="acknowledge that lawn reseeding is outside the corpus scope",
        ),
        TestCase(
            label="Q9: Water savings numbers",
            question="How much water can I expect to save in a year by switching to a native garden instead of a traditional lawn?",
            expected_keywords=["water", "save", "percent", "number"],
            expected_answer="acknowledge that specific water savings numbers are not in the documents",
        ),
        TestCase(
            label="Q10: Best month to plant roses",
            question="Which month should I plan to plant new roses in my garden?",
            expected_keywords=["month", "rose", "plant", "timing"],
            expected_answer="note that roses are outside scope; note general fall/early spring timing for natives",
        ),
    ]


def print_comparison_report(azure_result: ProviderResult, groq_result: ProviderResult):
    """Print a side-by-side comparison report."""
    print("\n" + "=" * 100)
    print("A/B COMPARISON REPORT")
    print("=" * 100)

    # Provider headers
    print(f"\n{'Question':<45} {'Azure':<20} {'Groq':<20} {'Winner':<10}")
    print("-" * 100)

    # Per-question comparison
    for azure_q, groq_q in zip(azure_result.responses, groq_result.responses):
        if "error" in azure_q or "error" in groq_q:
            continue

        label = azure_q.get("question", "Unknown")[:40]
        azure_avg = sum(
            azure_q["evaluations"][et]["score"]
            for et in ["correctness", "groundedness", "helpfulness"]
            if et in azure_q.get("evaluations", {})
        ) / 3 if azure_q.get("evaluations") else 0

        groq_avg = sum(
            groq_q["evaluations"][et]["score"]
            for et in ["correctness", "groundedness", "helpfulness"]
            if et in groq_q.get("evaluations", {})
        ) / 3 if groq_q.get("evaluations") else 0

        winner = "Azure" if azure_avg > groq_avg else "Groq" if groq_avg > azure_avg else "Tie"

        print(
            f"{label:<45} {azure_avg:>6.2f} "
            f"({azure_q.get('latency_ms', 0):>5.0f}ms) {groq_avg:>6.2f} "
            f"({groq_q.get('latency_ms', 0):>5.0f}ms) {winner:<10}"
        )

    # Dimension-level comparison
    print("\n" + "-" * 100)
    print("Average scores by dimension:")
    print("-" * 100)

    for dimension in ["correctness", "groundedness", "helpfulness"]:
        azure_score = azure_result.avg_scores.get(dimension, 0.0)
        groq_score = groq_result.avg_scores.get(dimension, 0.0)
        winner = "Azure" if azure_score > groq_score else "Groq" if groq_score > azure_score else "Tie"

        print(
            f"{dimension:<30} Azure: {azure_score:.3f}  |  "
            f"Groq: {groq_score:.3f}  |  Winner: {winner}"
        )

    # Overall summary
    print("\n" + "-" * 100)
    azure_overall = sum(azure_result.avg_scores.values()) / len(azure_result.avg_scores)
    groq_overall = sum(groq_result.avg_scores.values()) / len(groq_result.avg_scores)

    print(f"Overall average score:")
    print(f"  Azure:  {azure_overall:.3f}")
    print(f"  Groq:   {groq_overall:.3f}")
    print(f"  Winner: {'Azure' if azure_overall > groq_overall else 'Groq' if groq_overall > azure_overall else 'Tie'}")

    # Latency comparison
    print("\n" + "-" * 100)
    azure_latencies = [r.get("latency_ms", 0) for r in azure_result.responses if "error" not in r]
    groq_latencies = [r.get("latency_ms", 0) for r in groq_result.responses if "error" not in r]

    azure_avg_latency = sum(azure_latencies) / len(azure_latencies) if azure_latencies else 0
    groq_avg_latency = sum(groq_latencies) / len(groq_latencies) if groq_latencies else 0

    print(f"Average latency per query:")
    print(f"  Azure:  {azure_avg_latency:.0f}ms")
    print(f"  Groq:   {groq_avg_latency:.0f}ms")
    print(f"  Faster: {'Azure' if azure_avg_latency < groq_avg_latency else 'Groq'} "
          f"({abs(azure_avg_latency - groq_avg_latency):.0f}ms difference)")

    print("\n" + "=" * 100)


def main():
    parser = argparse.ArgumentParser(
        description="A/B evaluation comparing LLM providers for CX Knowledge Base RAG."
    )
    parser.add_argument(
        "--providers",
        default="azure,groq",
        help="Comma-separated list of providers to compare (default: azure,groq)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test connectivity without running full evaluation.",
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Path to .env file (default: .env)",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:3001",
        help="AnythingLLM base URL (default: http://localhost:3001)",
    )
    parser.add_argument(
        "--workspace",
        default="cx-knowledge-base",
        help="Workspace slug (default: cx-knowledge-base)",
    )
    parser.add_argument(
        "--groq-model",
        default="llama-3.3-70b-versatile",
        help="Groq model to use (default: llama-3.3-70b-versatile)",
    )
    parser.add_argument(
        "--azure-model",
        default="gpt-4o",
        help="Azure model to use (default: gpt-4o)",
    )

    args = parser.parse_args()

    # Load environment
    try:
        env = load_env(args.env)
    except FileNotFoundError as e:
        print(f"✗ {e}")
        sys.exit(1)

    # Check container
    print("\n[1] Container Health")
    if not check_container(args.base_url):
        print(f"✗ AnythingLLM container not running at {args.base_url}")
        print("  Hint: docker-compose up -d")
        sys.exit(1)
    print(f"✓ Container is online at {args.base_url}")

    # Check API key
    print("\n[2] Authentication")
    api_key = env.get("ANYWHERE_API_KEY")
    if not api_key:
        print("✗ ANYWHERE_API_KEY not set in .env")
        sys.exit(1)
    print(f"✓ API key configured")

    # Parse provider list
    providers = [p.strip() for p in args.providers.split(",")]
    if len(providers) < 2:
        print("✗ Must specify at least 2 providers to compare")
        sys.exit(1)

    # Dry-run: test connectivity only
    if args.dry_run:
        print("\n[3] Dry-run: testing connectivity...")
        test_query = "What is a native BC plant?"
        result = query_rag(args.base_url, api_key, args.workspace, test_query)
        if result:
            response = result.get("textResponse", "")[:100]
            print(f"✓ Chat endpoint responsive. Sample response: {response}...")
        else:
            print(f"✗ Chat endpoint failed")
            sys.exit(1)
        print("\n✓ Dry-run passed. Ready to run full A/B evaluation.")
        return

    # Get current provider to restore later
    print("\n[3] Checking current provider...")
    original_provider = get_current_provider(args.base_url, api_key, args.workspace)
    if not original_provider:
        print("✗ Failed to determine current provider. Aborting to prevent misconfiguration.")
        sys.exit(1)
    print(f"✓ Original provider: {original_provider['provider']}")

    # Initialize judge model (always use Azure gpt-4o as judge)
    print("\n[4] Initializing judge model (Azure gpt-4o)...")
    judge = build_judge_model(env)
    if not judge:
        print("  Warning: Judge model initialization failed. Will use keyword matching as fallback.")
    else:
        print("✓ Judge model ready")

    # Load test cases
    test_cases = build_test_cases()
    print(f"\n[5] Loaded {len(test_cases)} test cases")

    # Run evaluations for each provider
    results = {}
    try:
        for provider in providers:
            # Map provider to model
            if provider == "azure":
                model = args.azure_model
            elif provider == "groq":
                model = args.groq_model
                # Verify Groq API key
                if not env.get("GROQ_API_KEY"):
                    print(f"✗ GROQ_API_KEY not set in .env. Cannot evaluate Groq.")
                    continue
            else:
                print(f"✗ Unknown provider: {provider}")
                continue

            # Switch provider
            print(f"\n[6.{provider}] Switching to {provider}...")
            if not set_provider(args.base_url, api_key, args.workspace, provider, model):
                print(f"✗ Failed to switch to {provider}. Skipping.")
                continue

            # Run evaluation
            result = run_evaluation(
                args.base_url, api_key, args.workspace, judge, test_cases, provider
            )
            if result:
                result.model = model
                results[provider] = result

    finally:
        # Always restore original provider
        print(f"\n[7] Restoring original provider ({original_provider['provider']})...")
        if not set_provider(
            args.base_url, api_key, args.workspace,
            original_provider['provider'], original_provider['model']
        ):
            print(f"✗ WARNING: Failed to restore original provider!")
            print(f"   Workspace may be left with {list(results.keys())[-1] if results else 'unknown'} provider.")
        else:
            print(f"✓ Original provider restored")

    # Validate results
    if len(results) < 2:
        print(f"\n✗ Evaluation failed for one or more providers. Collected results: {list(results.keys())}")
        sys.exit(1)

    # Sort results by provider name to ensure consistent ordering
    provider_names = sorted(results.keys())
    result_list = [results[p] for p in provider_names]

    # Print comparison report
    if provider_names[0] == "azure" and provider_names[1] == "groq":
        print_comparison_report(result_list[0], result_list[1])
    elif provider_names[0] == "groq" and provider_names[1] == "azure":
        print_comparison_report(result_list[1], result_list[0])
    else:
        print("\nNote: Custom provider comparison (non-standard order)")
        for result in result_list:
            print(f"\n{result.provider.upper()}: avg scores = {result.avg_scores}")

    # Save JSON results
    print(f"\n[8] Saving results...")
    output_file = "docs/ab-results.json"
    output_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "providers": {
            name: {
                "provider": results[name].provider,
                "model": results[name].model,
                "avg_scores": results[name].avg_scores,
                "responses": results[name].responses,
            }
            for name in provider_names
        },
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"✓ Results saved to {output_file}")

    print(f"\n✓ A/B evaluation complete.")


if __name__ == "__main__":
    main()
