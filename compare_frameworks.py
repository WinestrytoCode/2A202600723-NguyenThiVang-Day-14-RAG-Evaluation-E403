"""
Exercise 3.4 — Framework Comparison.

Runs the same 20-QA golden dataset (run_benchmark.QA_DATA) through two
different evaluation frameworks and compares the scores:

  Framework 1: RAGASEvaluator (this lab's word-overlap heuristic, no LLM,
               no external dependency, partial credit).
  Framework 2: DeepEval's ExactMatchMetric (industry library, no LLM judge
               needed, strict binary string equality).

Both frameworks are non-LLM here (no OPENAI_API_KEY / paid Anthropic calls
involved) — see exercises.md Exercise 3.4 for the discussion of what that
means for the comparison.
"""

import json

from deepeval.metrics import ExactMatchMetric
from deepeval.test_case import LLMTestCase

from run_benchmark import QA_DATA, mock_agent_factory
from template import BenchmarkRunner, QAPair, RAGASEvaluator


def main() -> None:
    qa_pairs = [
        QAPair(
            question=item["question"],
            expected_answer=item["expected_answer"],
            context=item["context"],
            metadata={"id": item["id"]},
        )
        for item in QA_DATA
    ]

    evaluator = RAGASEvaluator()
    runner = BenchmarkRunner()
    agent_fn = mock_agent_factory()

    # Framework 1 — RAGASEvaluator
    f1_results = runner.run(qa_pairs, agent_fn, evaluator)
    for r, original in zip(f1_results, qa_pairs):
        r.qa_pair = original

    # Framework 2 — DeepEval ExactMatchMetric (run on the SAME agent answers)
    exact_match = ExactMatchMetric()
    f2_scores = []
    for pair, f1_result in zip(qa_pairs, f1_results):
        test_case = LLMTestCase(
            input=pair.question,
            actual_output=f1_result.actual_answer,
            expected_output=pair.expected_answer,
        )
        score = exact_match.measure(test_case, _show_indicator=False)
        f2_scores.append(score)

    rows = []
    for pair, f1_result, f2_score in zip(qa_pairs, f1_results, f2_scores):
        rows.append(
            {
                "id": pair.metadata["id"],
                "f1_overall": round(f1_result.overall_score(), 3),
                "f1_passed": f1_result.passed,
                "f2_exact_match": f2_score,
                "f2_passed": f2_score >= 1.0,
                "agree": f1_result.passed == (f2_score >= 1.0),
            }
        )

    print("=== Per-item comparison ===")
    for row in rows:
        print(
            f"{row['id']:>4} | F1 overall={row['f1_overall']:.3f} passed={row['f1_passed']!s:5} "
            f"| F2 exact_match={row['f2_exact_match']:.1f} passed={row['f2_passed']!s:5} "
            f"| agree={row['agree']}"
        )

    n = len(rows)
    f1_pass_rate = sum(r["f1_passed"] for r in rows) / n
    f2_pass_rate = sum(r["f2_passed"] for r in rows) / n
    agreement_rate = sum(r["agree"] for r in rows) / n
    f1_avg = sum(r["f1_overall"] for r in rows) / n
    f2_avg = sum(r["f2_exact_match"] for r in rows) / n

    summary = {
        "n": n,
        "framework1_ragas_heuristic": {"avg_score": round(f1_avg, 3), "pass_rate": round(f1_pass_rate, 3)},
        "framework2_deepeval_exact_match": {"avg_score": round(f2_avg, 3), "pass_rate": round(f2_pass_rate, 3)},
        "agreement_rate": round(agreement_rate, 3),
    }

    print("\n=== Summary ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
