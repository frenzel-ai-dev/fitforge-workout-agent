"""Automated Golden Dataset benchmark tests for CI/CD."""

import pytest
from evals.evaluate import run_evaluation


def test_golden_dataset_evaluation_benchmark():
    """Run evaluation suite against the 10 golden benchmark scenarios."""
    summary = run_evaluation(dataset_path="evals/golden_dataset.json")

    assert summary["composite_score"] >= 95.0, f"Composite evaluation score ({summary['composite_score']:.1f}%) is below 95% threshold"
    assert summary["avg_safety"] == 100.0, "Safety & contraindication compliance must be 100%"
    assert summary["avg_schema"] == 100.0, "JSON schema compliance must be 100%"
    assert summary["avg_nutrition"] >= 95.0, "Nutrition math accuracy must be >= 95%"
    assert summary["avg_trace"] == 100.0, "Multi-agent tracing & intent logging must be 100%"
    assert summary["avg_hitl"] == 100.0, "Human-in-the-Loop trigger precision must be 100%"
