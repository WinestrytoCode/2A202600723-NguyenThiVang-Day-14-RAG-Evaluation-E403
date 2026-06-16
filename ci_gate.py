"""
CI/CD quality gate for the Intake Assistant agent.

Run as: python ci_gate.py
Exit code 0 = pass (deploy allowed), 1 = fail (block deploy).

Policy is taken directly from this lab's own analysis:
  - Absolute thresholds come from exercises.md Exercise 1.3.
  - Block-vs-alert split on regression comes from reflection.md Section 5
    Câu 3: faithfulness/safety regressions block; relevance/completeness
    regressions only alert (they're more exposed to the word-overlap
    metric's false positives — see exercises.md Exercise 3.2).
"""

import json
import sys
from pathlib import Path

from run_benchmark import QA_DATA, mock_agent_factory
from template import BenchmarkRunner, QAPair, RAGASEvaluator

THRESHOLDS = {
    "avg_faithfulness": 0.7,
    "avg_relevance": 0.6,
    "avg_completeness": 0.6,
}
BLOCKING_REGRESSION_METRICS = {"avg_faithfulness"}
REGRESSION_DELTA = 0.05
BASELINE_PATH = Path(__file__).parent / "baseline_report.json"


def run_benchmark() -> dict:
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
    results = runner.run(qa_pairs, mock_agent_factory(), evaluator)
    return runner.generate_report(results)


def main() -> int:
    report = run_benchmark()
    print("=== Benchmark report ===")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    failed_gates = [name for name, threshold in THRESHOLDS.items() if report[name] < threshold]
    if failed_gates:
        print(f"\nBLOCKED: below required threshold: {failed_gates}")
        return 1

    if BASELINE_PATH.exists():
        baseline = json.loads(BASELINE_PATH.read_text())
        regressions = [
            name for name in THRESHOLDS if baseline.get(name, 0) - report[name] > REGRESSION_DELTA
        ]
        blocking = [r for r in regressions if r in BLOCKING_REGRESSION_METRICS]
        soft = [r for r in regressions if r not in BLOCKING_REGRESSION_METRICS]

        if soft:
            print(f"\nALERT (non-blocking): regression vs baseline in {soft}")
        if blocking:
            print(f"\nBLOCKED: regression vs baseline in {blocking}")
            return 1
    else:
        print(f"\nNo baseline found at {BASELINE_PATH.name} — skipping regression check. "
              "Run once and commit the file to enable it.")

    print("\nPASSED: all gates OK, deploy allowed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
