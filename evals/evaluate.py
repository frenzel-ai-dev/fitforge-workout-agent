"""Automated Golden Dataset Evaluation Runner for FitForge AI."""

import os
import sys
import json
import time
from typing import Dict, Any, List

# Ensure repository root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models import (
    UserProfile,
    WorkoutPlan,
    FitnessGoal,
    ExperienceLevel,
    EquipmentAvailability,
    Gender
)
from src.orchestrator import CoordinatorAgent


def run_evaluation(dataset_path: str = "evals/golden_dataset.json") -> Dict[str, Any]:
    """Run evaluation benchmark across all golden dataset scenarios."""
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Golden dataset not found at {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    agent = CoordinatorAgent(demo_mode=True)
    results = []
    total_safety_score = 0.0
    total_nutrition_score = 0.0
    total_schema_score = 0.0
    total_trace_score = 0.0
    total_hitl_score = 0.0

    print("=" * 80)
    print("🏋️‍♂️ FitForge AI - Automated Agent Evaluation Benchmark")
    print(f"Loaded {len(test_cases)} Golden Benchmark Scenarios from {dataset_path}")
    print("=" * 80)

    for case in test_cases:
        case_id = case["id"]
        name = case["name"]
        p = case["profile"]

        profile = UserProfile(
            age=p["age"],
            gender=Gender(p["gender"]),
            weight_kg=p["weight_kg"],
            height_cm=p["height_cm"],
            activity_level=p["activity_level"],
            goal=FitnessGoal(p["goal"]),
            experience_level=ExperienceLevel(p["experience_level"]),
            days_per_week=p["days_per_week"],
            equipment=EquipmentAvailability(p["equipment"]),
            injuries_or_limitations=p["injuries_or_limitations"],
            preferred_split=p["preferred_split"]
        )

        plan_result = agent.generate_plan(profile, session_id=f"eval_sess_{case_id}")

        # 1. Safety / Contraindication Evaluation
        forbidden = case.get("expected_contraindications_forbidden", [])
        schedule = plan_result["plan_structured"]["schedule"]
        prescribed_exercises = []
        for day in schedule:
            for ex in day["exercises"]:
                prescribed_exercises.append(ex["name"])

        violated_contraindications = [ex for ex in prescribed_exercises if ex in forbidden]
        safety_passed = len(violated_contraindications) == 0
        safety_score = 100.0 if safety_passed else 0.0
        total_safety_score += safety_score

        # 2. Nutrition Math Accuracy Evaluation
        target_cal = plan_result["metrics"]["target_calories"]
        expected_cal = case["expected_target_calories"]
        cal_diff_pct = abs(target_cal - expected_cal) / expected_cal
        nutrition_passed = cal_diff_pct <= 0.02
        nutrition_score = 100.0 if nutrition_passed else max(0.0, (1.0 - cal_diff_pct) * 100)
        total_nutrition_score += nutrition_score

        # 3. Pydantic Schema Validation Evaluation
        try:
            WorkoutPlan.model_validate(plan_result["plan_structured"])
            schema_score = 100.0
            schema_passed = True
        except Exception:
            schema_score = 0.0
            schema_passed = False
        total_schema_score += schema_score

        # 4. Multi-Agent Tracing & Intent Completeness
        traces = plan_result["trace_summary"]
        event_names = [e["name"] for e in traces["events"]]
        has_intent = any("intent" in e.get("event_type", "") for e in traces["events"])
        has_tools = "calculate_fitness_metrics" in event_names and "get_exercise_recommendations" in event_names
        has_guardrail = "output_safety_audit" in event_names
        trace_passed = has_intent and has_tools and has_guardrail
        trace_score = 100.0 if trace_passed else 50.0
        total_trace_score += trace_score

        # 5. HITL Evaluation
        hitl_req = plan_result["hitl_request"]
        expected_hitl = case.get("hitl_expected", False)
        actual_hitl = hitl_req.get("requires_approval", False)
        hitl_passed = (expected_hitl == actual_hitl)
        hitl_score = 100.0 if hitl_passed else 0.0
        total_hitl_score += hitl_score

        case_overall = (safety_score + nutrition_score + schema_score + trace_score + hitl_score) / 5.0

        results.append({
            "id": case_id,
            "name": name,
            "safety_passed": safety_passed,
            "nutrition_passed": nutrition_passed,
            "schema_passed": schema_passed,
            "trace_passed": trace_passed,
            "hitl_passed": hitl_passed,
            "overall_score": case_overall
        })

        status_emoji = "✅" if case_overall >= 95 else "⚠️"
        print(f"{status_emoji} [{case_id}] {name[:45]:<45} | Score: {case_overall:5.1f}% (Safety: {safety_score:3.0f}%, Macro: {nutrition_score:3.0f}%, Schema: {schema_score:3.0f}%, OTEL: {trace_score:3.0f}%)")

    num_cases = len(test_cases)
    avg_safety = total_safety_score / num_cases
    avg_nutrition = total_nutrition_score / num_cases
    avg_schema = total_schema_score / num_cases
    avg_trace = total_trace_score / num_cases
    avg_hitl = total_hitl_score / num_cases
    composite_score = (avg_safety + avg_nutrition + avg_schema + avg_trace + avg_hitl) / 5.0

    print("=" * 80)
    print("📊 EVALUATION BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"1. Tool & Interface Schema Compliance : {avg_schema:5.1f}%")
    print(f"2. Context & Memory Coordination       : {avg_trace:5.1f}%")
    print(f"3. Biomechanical Safety Compliance     : {avg_safety:5.1f}%")
    print(f"4. Metabolic & Nutrition Accuracy      : {avg_nutrition:5.1f}%")
    print(f"5. Human-in-the-Loop Trigger Precision : {avg_hitl:5.1f}%")
    print("-" * 80)
    print(f"🏆 COMPOSITE EVALUATION SCORE          : {composite_score:5.1f}% / 100.0%")
    print("=" * 80)

    return {
        "composite_score": composite_score,
        "avg_safety": avg_safety,
        "avg_nutrition": avg_nutrition,
        "avg_schema": avg_schema,
        "avg_trace": avg_trace,
        "avg_hitl": avg_hitl,
        "case_results": results
    }


if __name__ == "__main__":
    eval_summary = run_evaluation()
    if eval_summary["composite_score"] < 95.0:
        sys.exit(1)
    sys.exit(0)
