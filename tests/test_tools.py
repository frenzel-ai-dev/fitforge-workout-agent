"""Unit tests for deterministic fitness calculation and exercise lookup tools."""

import pytest
from src.tools import (
    calculate_fitness_metrics,
    calculate_one_rep_max,
    get_exercise_recommendations,
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

    # Mifflin-St Jeor check: 10*80 + 6.25*180 - 5*30 + 5 = 800 + 1125 - 150 + 5 = 1780
    assert metrics["bmr_calories"] == 1780
    # TDEE = 1780 * 1.55 = 2759
    assert metrics["tdee_calories"] == 2759
    # Hypertrophy target = 2759 + 300 = 3059
    assert metrics["target_calories"] == 3059
    # Protein: 80 * 2.0 = 160g
    assert metrics["protein_g"] == 160
    assert metrics["hydration_liters"] > 2.5
    assert metrics["carbs_g"] > 0
    assert metrics["fats_g"] > 0


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

    # Mifflin-St Jeor female: 10*60 + 6.25*165 - 5*28 - 161 = 600 + 1031.25 - 140 - 161 = 1330.25 -> 1330
    assert metrics["bmr_calories"] == 1330
    # TDEE = 1330 * 1.2 = 1596
    assert metrics["tdee_calories"] == 1596
    # Fat loss target = 1596 - 500 = 1096 -> min clamped to 1200
    assert metrics["target_calories"] == 1200
    # Protein: 60 * 2.0 = 120g
    assert metrics["protein_g"] == 120


def test_calculate_one_rep_max():
    """Test 1RM calculations with Epley and Brzycki formulas."""
    result = calculate_one_rep_max(weight=100.0, reps=5)
    # Epley: 100 * (1 + 5/30) = 116.67
    # Brzycki: 100 * (36 / 32) = 112.5
    # Avg: ~114.6
    assert 112.0 <= result["estimated_1rm"] <= 118.0
    assert "hypertrophy_70_80%" in result["zones"]


def test_get_exercise_recommendations_equipment_filter():
    """Test filtering by equipment availability."""
    dumbbell_exercises = get_exercise_recommendations(equipment="Dumbbell")
    assert len(dumbbell_exercises) > 0
    for ex in dumbbell_exercises:
        assert ex["equipment"] in ["Dumbbell", "Bodyweight"]


def test_get_exercise_recommendations_injury_filter():
    """Test filtering out contraindicated exercises when injuries are specified."""
    # Knee injury should filter out Barbell Back Squat
    knee_safe_exercises = get_exercise_recommendations(injury_avoidance="knee pain")
    names = [e["name"] for e in knee_safe_exercises]
    assert "Barbell Back Squat" not in names

    # Lower back pain should filter out Barbell Bent-Over Row
    back_safe_exercises = get_exercise_recommendations(injury_avoidance="lower back pain")
    back_names = [e["name"] for e in back_safe_exercises]
    assert "Barbell Bent-Over Row" not in back_names


def test_exercise_database_integrity():
    """Verify all exercises in database have required schema fields."""
    for ex in EXERCISE_DATABASE:
        assert "name" in ex
        assert "muscle" in ex
        assert "equipment" in ex
        assert "contraindications" in ex
        assert "cues" in ex
