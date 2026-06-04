#!/usr/bin/env python3
"""
eval_rag.py — RAG evaluation suite for CX Knowledge Base (AnythingLLM)

Uses openevals (LangChain evaluators) to assess RAG system quality:
  - Correctness: Does the answer match expected facts?
  - Groundedness: Is the answer grounded in retrieved context?
  - Helpfulness: Is the response useful and complete?

Usage:
  python3 scripts/eval_rag.py              # Run full evaluation
  python3 scripts/eval_rag.py --dry-run    # Test connectivity only
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Optional

import requests
from openevals import prompts
from openevals.llm import create_llm_as_judge
from langchain_openai import AzureChatOpenAI


@dataclass
class TestCase:
    """A single evaluation test case."""
    label: str
    question: str
    expected_keywords: list[str]
    expected_answer: str


def load_env(env_path: str = ".env") -> dict:
    """Load environment variables from .env file."""
    env = {}
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"{env_path} not found. See .env.example.")

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, val = line.split("=", 1)
                env[key] = val.strip("'\"")

    return env


def check_container(base_url: str) -> bool:
    """Check if AnythingLLM container is running."""
    try:
        resp = requests.get(f"{base_url}/api/ping", timeout=2)
        data = resp.json()
        return data.get("online", False)
    except Exception as e:
        print(f"✗ Container check failed: {e}")
        return False


def build_judge_model(env: dict):
    """Build Azure OpenAI judge model for evaluation."""
    try:
        # Extract Azure config from env
        api_key = env.get("AZURE_OPENAI_KEY")
        endpoint = env.get("AZURE_OPENAI_ENDPOINT")
        model = env.get("AZURE_OPENAI_MODEL_PREF", "gpt-4o")

        if not api_key or not endpoint:
            raise ValueError("AZURE_OPENAI_KEY or AZURE_OPENAI_ENDPOINT not set")

        # Parse endpoint to extract base resource URL
        # Expected format: https://{resource}.openai.azure.com/openai/deployments/{deployment}/...
        base_endpoint = endpoint.split("/openai/deployments/")[0]

        judge = AzureChatOpenAI(
            api_key=api_key,
            api_version="2024-08-01-preview",
            azure_endpoint=base_endpoint,
            model=model,
        )

        return judge
    except Exception as e:
        print(f"✗ Failed to initialize Azure OpenAI judge: {e}")
        return None


def query_rag(base_url: str, api_key: str, workspace: str, question: str) -> Optional[dict]:
    """Query the RAG system."""
    url = f"{base_url}/api/v1/workspace/{workspace}/chat"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "message": question,
        "mode": "query",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"✗ Query failed: {e}")
        return None


def evaluate_response(
    response_text: str,
    question: str,
    expected_keywords: list[str],
    expected_answer: str,
    retrieved_context: str,
    judge_model,
    eval_type: str,
) -> dict:
    """
    Evaluate a single response using openevals.

    eval_type: "correctness" | "groundedness" | "helpfulness"
    """
    if not judge_model:
        # No judge model, fall back to keyword matching only
        matched = sum(
            1 for kw in expected_keywords
            if kw.lower() in response_text.lower()
        )
        return {
            "score": 0.5 if matched > 0 else 0.0,
            "method": "keyword_fallback",
            "matched_keywords": matched,
            "total_keywords": len(expected_keywords),
        }

    try:
        # Select appropriate prompt and build evaluator
        if eval_type == "correctness":
            prompt = prompts.CORRECTNESS_PROMPT
            evaluator = create_llm_as_judge(
                prompt=prompt,
                feedback_key="score",
                judge=judge_model,
                continuous=True,
            )
            result = evaluator(
                inputs=question,
                outputs=response_text,
                reference_outputs=expected_answer,
            )
        elif eval_type == "groundedness":
            # Groundedness requires context — fill in the template
            prompt = prompts.RAG_GROUNDEDNESS_PROMPT.format(
                context=retrieved_context,
                outputs=response_text,
            )
            evaluator = create_llm_as_judge(
                prompt=prompt,
                feedback_key="score",
                judge=judge_model,
                continuous=True,
            )
            result = evaluator(
                inputs=question,
                outputs=response_text,
            )
        elif eval_type == "helpfulness":
            prompt = prompts.RAG_HELPFULNESS_PROMPT
            evaluator = create_llm_as_judge(
                prompt=prompt,
                feedback_key="score",
                judge=judge_model,
                continuous=True,
            )
            result = evaluator(
                inputs=question,
                outputs=response_text,
            )
        else:
            raise ValueError(f"Unknown eval_type: {eval_type}")

        return {
            "score": result.get("score", 0.0),
            "method": "llm_judge",
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as e:
        print(f"  Evaluation error ({eval_type}): {e}")
        return {"score": 0.0, "method": "error", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate CX Knowledge Base RAG system with openevals."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test connectivity without running evaluations.",
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

    # Dry-run: just test connectivity
    if args.dry_run:
        print("\n[3] Dry-run: testing connectivity to chat endpoint...")
        test_query = "What is a native BC plant?"
        result = query_rag(args.base_url, api_key, args.workspace, test_query)
        if result:
            response = result.get("textResponse", "")[:100]
            print(f"✓ Chat endpoint responsive. Sample response: {response}...")
        else:
            print(f"✗ Chat endpoint failed")
            sys.exit(1)
        print("\n✓ Dry-run passed. Ready to run full evaluation.")
        return

    # Full evaluation
    print("\n[3] Initializing judge model...")
    judge = build_judge_model(env)
    if not judge:
        print("  Warning: Judge model initialization failed. Will use keyword matching as fallback.")
    else:
        print("✓ Judge model ready")

    # Test cases from existing test.sh
    test_cases = [
        TestCase(
            label="Shade-tolerant plants",
            question="What native plants grow well in shade?",
            expected_keywords=["salal", "huckleberry", "Oregon-grape", "fern", "shade"],
            expected_answer="salal, huckleberry, Oregon grape, and various ferns",
        ),
        TestCase(
            label="Butterfly-attracting plants",
            question="What plants attract butterflies?",
            expected_keywords=["butterfly", "nectar", "flower", "native"],
            expected_answer="native flowers with nectar",
        ),
        TestCase(
            label="Edible BC plants",
            question="What edible native plants are in BC?",
            expected_keywords=["berry", "edible", "salal", "huckleberry", "native"],
            expected_answer="salal, huckleberries, and other edible berries",
        ),
        TestCase(
            label="Drought-tolerant plants",
            question="Which native BC plants are drought-tolerant?",
            expected_keywords=["drought", "water", "dry", "sage", "native"],
            expected_answer="native plants adapted to dry conditions",
        ),
        TestCase(
            label="Ground covers",
            question="What are good ground cover plants for BC gardens?",
            expected_keywords=["ground", "cover", "low", "native", "spreading"],
            expected_answer="low-growing spreading native plants",
        ),
    ]

    print(f"\n[4] Running evaluations ({len(test_cases)} test cases)")
    print("-" * 70)

    results = []
    for i, tc in enumerate(test_cases, 1):
        print(f"\n{i}. {tc.label}")
        print(f"   Q: {tc.question}")

        # Query the RAG system
        rag_result = query_rag(args.base_url, api_key, args.workspace, tc.question)
        if not rag_result:
            print("   ✗ Query failed")
            results.append({"test_case": tc.label, "error": "query_failed"})
            continue

        response_text = rag_result.get("textResponse", "")
        if not response_text:
            print("   ✗ No response returned")
            results.append({"test_case": tc.label, "error": "empty_response"})
            continue

        # Extract retrieved context from sources
        sources = rag_result.get("sources", [])
        retrieved_context = "\n".join(
            source.get("text", "")[:500] for source in sources
        ) if sources else response_text

        print(f"   A: {response_text[:150]}...")

        # Evaluate on multiple dimensions
        test_result = {
            "test_case": tc.label,
            "response": response_text,
            "evaluations": {},
        }

        for eval_type in ["correctness", "groundedness", "helpfulness"]:
            eval_result = evaluate_response(
                response_text,
                tc.question,
                tc.expected_keywords,
                tc.expected_answer,
                retrieved_context,
                judge,
                eval_type,
            )
            score = eval_result.get("score", 0.0)
            method = eval_result.get("method", "unknown")

            test_result["evaluations"][eval_type] = eval_result

            # Score display
            if score >= 0.7:
                status = "✓"
            elif score >= 0.5:
                status = "~"
            else:
                status = "✗"

            print(f"   {status} {eval_type}: {score:.2f} ({method})")

        results.append(test_result)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total_evals = 0
    passed_evals = 0

    for result in results:
        label = result["test_case"]
        evals = result.get("evaluations", {})

        if not evals:
            print(f"✗ {label}: no evaluations (query/parse error)")
            continue

        avg_score = sum(e.get("score", 0) for e in evals.values()) / len(evals)
        passed = sum(1 for e in evals.values() if e.get("score", 0) >= 0.7)
        total_evals += len(evals)
        passed_evals += passed

        status = "✓ PASS" if avg_score >= 0.7 else "✗ FAIL"
        print(f"{status}  {label}: {avg_score:.2f} avg ({passed}/{len(evals)} dimensions >= 0.7)")

    print("-" * 70)
    if total_evals > 0:
        pass_rate = passed_evals / total_evals
        print(f"Overall: {passed_evals}/{total_evals} evaluations passed ({pass_rate*100:.1f}%)")
        if pass_rate >= 0.7:
            print("✓ RAG system is performing well.")
            sys.exit(0)
        else:
            print("✗ RAG system needs improvement.")
            sys.exit(1)
    else:
        print("✗ No evaluations completed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
