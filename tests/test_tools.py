"""Unit tests for deterministic fitness calculation, exercise lookup, and guided error handling tools."""

import pytest
from src.tools import (
    calculate_fitness_metrics,
    calculate_one_rep_max,
    get_exercise_recommendations,
    verify_exercise_safety,
    calculate_heart_rate_zones,
    execute_tool_with_recovery,
    TOOL_DECLARATIONS,
    EXERCISE_DATABASE
)


def test_calculate_fitness_metrics_male():
    """Test BMR, TDEE, and macro calculation for male athlete."""
    metrics = calculate_fitness_metrics(
        weight_kg=80.0,
        height_cm=180.0,
        age=30,
        gender="Male",
        activity_level="Moderately Active (exercise 3-5 days/wk)",
        goal="Hypertrophy (Muscle Gain)"
    )
    assert metrics["bmr_calories"] == 1780
    assert metrics["tdee_calories"] == 2759
    assert metrics["target_calories"] == 3059
    assert metrics["protein_g"] == 160
    assert metrics["hydration_liters"] > 2.5


def test_calculate_fitness_metrics_female_fat_loss():
    """Test BMR and caloric deficit calculation for female athlete."""
    metrics = calculate_fitness_metrics(
        weight_kg=60.0,
        height_cm=165.0,
        age=28,
        gender="Female",
        activity_level="Sedentary (desk job, little exercise)",
        goal="Fat Loss & Conditioning"
    )
    assert metrics["bmr_calories"] == 1330
    assert metrics["tdee_calories"] == 1596
    assert metrics["target_calories"] == 1200
    assert metrics["protein_g"] == 120


def test_calculate_one_rep_max():
    """Test 1RM calculations with Epley and Brzycki formulas."""
    result = calculate_one_rep_max(weight=100.0, reps=5)
    assert 112.0 <= result["estimated_1rm"] <= 118.0
    assert "hypertrophy_70_80%" in result["zones"]


def test_verify_exercise_safety():
    """Test individual exercise safety verification against injuries."""
    # Knee pain vs Squat
    res_squat = verify_exercise_safety("Barbell Back Squat", "knee pain")
    assert res_squat["is_safe"] is False
    assert res_squat["risk_level"] == "HIGH"
    assert res_squat["alternative"] is not None

    # Lower back pain vs Chest Supported Row (Safe)
    res_row = verify_exercise_safety("Chest-Supported Dumbbell Row", "lower back pain")
    assert res_row["is_safe"] is True

    # No injuries
    res_clean = verify_exercise_safety("Barbell Bench Press", "None")
    assert res_clean["is_safe"] is True


def test_calculate_heart_rate_zones():
    """Test cardiovascular heart rate zones calculation."""
    res = calculate_heart_rate_zones(age=30, resting_hr=60)
    assert res["max_heart_rate"] == 187
    assert "zone_2_endurance" in res["zones"]


def test_execute_tool_with_recovery():
    """Test guided error handling and structured recovery hints for LLM."""
    # Valid call
    valid_res = execute_tool_with_recovery(
        "calculate_fitness_metrics",
        {"weight_kg": 75.0, "height_cm": 175.0, "age": 25}
    )
    assert valid_res["status"] == "success"

    # Out of bounds value error
    oob_res = execute_tool_with_recovery(
        "calculate_fitness_metrics",
        {"weight_kg": 500.0, "height_cm": 175.0, "age": 25}
    )
    assert oob_res["status"] == "error"
    assert oob_res["error_type"] == "VALUE_OUT_OF_BOUNDS"
    assert "retry_guidance" in oob_res

    # Unknown tool
    unknown_res = execute_tool_with_recovery("unknown_fitness_tool", {})
    assert unknown_res["status"] == "error"
    assert unknown_res["error_type"] == "TOOL_NOT_FOUND"


def test_tool_declarations_schema():
    """Test that all tool declarations have valid JSON schema definitions."""
    assert len(TOOL_DECLARATIONS) >= 5
    for tool_dec in TOOL_DECLARATIONS:
        assert "name" in tool_dec
        assert "description" in tool_dec
        assert "parameters" in tool_dec
        assert tool_dec["parameters"]["type"] == "object"
        assert "properties" in tool_dec["parameters"]
