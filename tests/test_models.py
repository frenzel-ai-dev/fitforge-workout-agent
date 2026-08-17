"""Unit tests for FitForge AI Pydantic data models and schemas."""

import pytest
from src.models import (
    UserProfile,
    WorkoutPlan,
    WorkoutDay,
    ExerciseItem,
    NutritionSummary,
    PeriodizationProgression,
    SafetyAuditResult,
    HITLActionRequest,
    FitnessGoal,
    ExperienceLevel,
    EquipmentAvailability,
    Gender,
    RiskLevel
)


def test_user_profile_validation():
    """Test UserProfile schema and validators."""
    profile = UserProfile(
        age=30,
        gender=Gender.MALE,
        weight_kg=78.0,
        height_cm=178.0,
        goal=FitnessGoal.HYPERTROPHY,
        experience_level=ExperienceLevel.INTERMEDIATE,
        days_per_week=4,
        equipment=EquipmentAvailability.FULL_GYM,
        injuries_or_limitations="   "
    )
    assert profile.injuries_or_limitations == "None"
    assert profile.weight_kg == 78.0


def test_exercise_item_schema():
    """Test ExerciseItem model and default fields."""
    item = ExerciseItem(
        name="Barbell Bench Press",
        target_muscle="Chest",
        sets=4,
        reps="6-8",
        rest_seconds=120,
        form_cue="Retract scapulae",
        alternative="Dumbbell Bench Press"
    )
    assert item.name == "Barbell Bench Press"
    assert item.sets == 4
    assert item.tempo == "3-0-1-0"


def test_workout_plan_json_schema():
    """Test WorkoutPlan schema export and JSON serialization."""
    day = WorkoutDay(
        day_name="Day 1: Upper Body",
        focus="Chest, Back",
        warmup=["Arm circles"],
        exercises=[
            ExerciseItem(name="Push-Ups", target_muscle="Chest", sets=3, reps="10-12")
        ]
    )
    nutrition = NutritionSummary(
        bmr_calories=1750,
        tdee_calories=2700,
        target_calories=3000,
        protein_g=160,
        carbs_g=350,
        fats_g=80,
        hydration_liters=3.5
    )
    plan = WorkoutPlan(
        plan_title="Hypertrophy 3-Day Plan",
        split_type="Push / Pull / Legs",
        frequency_days=3,
        schedule=[day],
        nutrition=nutrition
    )
    json_data = plan.model_dump()
    assert json_data["plan_title"] == "Hypertrophy 3-Day Plan"
    assert len(json_data["schedule"]) == 1
    assert json_data["nutrition"]["target_calories"] == 3000
