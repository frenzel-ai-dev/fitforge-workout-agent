"""Unit and integration tests for WorkoutAgent and UserProfile models."""

import pytest
from src.models import (
    UserProfile,
    FitnessGoal,
    ExperienceLevel,
    EquipmentAvailability,
    Gender
)
from src.agent import WorkoutAgent
from src.observability import ExecutionTracer


def test_user_profile_creation():
    """Test UserProfile initialization and validation."""
    profile = UserProfile(
        age=25,
        gender=Gender.FEMALE,
        weight_kg=65.0,
        height_cm=170.0,
        goal=FitnessGoal.STRENGTH,
        experience_level=ExperienceLevel.INTERMEDIATE,
        days_per_week=4,
        equipment=EquipmentAvailability.FULL_GYM,
        injuries_or_limitations="shoulder impingement"
    )
    assert profile.age == 25
    assert profile.weight_kg == 65.0
    assert profile.goal == FitnessGoal.STRENGTH


def test_workout_agent_demo_plan_generation():
    """Test WorkoutAgent plan generation in offline demo mode."""
    agent = WorkoutAgent(demo_mode=True)
    profile = UserProfile(
        age=29,
        gender=Gender.MALE,
        weight_kg=75.0,
        height_cm=178.0,
        goal=FitnessGoal.HYPERTROPHY,
        experience_level=ExperienceLevel.INTERMEDIATE,
        days_per_week=4,
        equipment=EquipmentAvailability.FULL_GYM,
        injuries_or_limitations="None"
    )

    result = agent.generate_plan(profile)

    assert "plan_markdown" in result
    assert "metrics" in result
    assert "trace_summary" in result
    assert len(result["plan_markdown"]) > 100
    assert "Day 1:" in result["plan_markdown"]
    assert "Progressive Overload" in result["plan_markdown"]
    assert "Nutrition & Recovery" in result["plan_markdown"]

    # Verify trace events recorded
    traces = result["trace_summary"]
    assert traces["total_events"] >= 3
    event_names = [e["name"] for e in traces["events"]]
    assert "calculate_fitness_metrics" in event_names
    assert "get_exercise_recommendations" in event_names
    assert "generate_plan" in event_names


def test_workout_agent_chat_interaction():
    """Test multi-turn chat responses from the WorkoutAgent."""
    agent = WorkoutAgent(demo_mode=True)
    profile = UserProfile(
        age=30,
        weight_kg=80.0,
        goal=FitnessGoal.FAT_LOSS,
        days_per_week=3
    )
    agent.generate_plan(profile)

    # Ask follow-up question
    response = agent.chat("Can you swap squats for another quad exercise?")
    assert len(response) > 20
    assert len(agent.chat_history) >= 3


def test_execution_tracer():
    """Test ExecutionTracer records duration and handles summaries."""
    tracer = ExecutionTracer()
    tracer.record_event(
        event_type="test_event",
        name="unit_test_step",
        duration_ms=45.2,
        input_data={"param": 1},
        output_summary="Success"
    )
    summary = tracer.get_summary()
    assert summary["total_events"] == 1
    assert summary["events"][0]["name"] == "unit_test_step"
    assert summary["events"][0]["duration_ms"] == 45.2
