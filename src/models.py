"""Data models and schemas for the Workout Planning Agent."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class FitnessGoal(str, Enum):
    HYPERTROPHY = "Hypertrophy (Muscle Gain)"
    STRENGTH = "Strength & Power"
    FAT_LOSS = "Fat Loss & Conditioning"
    ENDURANCE = "Endurance & Stamina"
    GENERAL_HEALTH = "General Health & Mobility"


class ExperienceLevel(str, Enum):
    BEGINNER = "Beginner (< 1 year)"
    INTERMEDIATE = "Intermediate (1-3 years)"
    ADVANCED = "Advanced (3+ years)"


class EquipmentAvailability(str, Enum):
    FULL_GYM = "Full Commercial Gym (Barbells, Dumbbells, Cables, Machines)"
    HOME_DUMBBELLS = "Home Gym (Dumbbells & Bench)"
    BODYWEIGHT_ONLY = "Calisthenics / Bodyweight Only"
    RESISTANCE_BANDS = "Bands & Bodyweight"


class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other / Non-binary"


class UserProfile(BaseModel):
    """User profile containing biometric info, goals, and training constraints."""
    age: int = Field(default=30, ge=14, le=100, description="Age in years")
    gender: Gender = Field(default=Gender.MALE, description="Gender for metabolic estimates")
    weight_kg: float = Field(default=75.0, ge=30.0, le=300.0, description="Body weight in kilograms")
    height_cm: float = Field(default=175.0, ge=100.0, le=250.0, description="Height in centimeters")
    activity_level: str = Field(
        default="Moderately Active (exercise 3-5 days/wk)",
        description="Daily non-exercise activity level"
    )
    goal: FitnessGoal = Field(default=FitnessGoal.HYPERTROPHY, description="Primary fitness objective")
    experience_level: ExperienceLevel = Field(default=ExperienceLevel.INTERMEDIATE, description="Lifting experience")
    days_per_week: int = Field(default=4, ge=2, le=7, description="Number of training days per week")
    equipment: EquipmentAvailability = Field(
        default=EquipmentAvailability.FULL_GYM,
        description="Available training equipment"
    )
    injuries_or_limitations: Optional[str] = Field(
        default="None",
        description="Injuries, joint pain, or movement restrictions (e.g., lower back pain, bad knees)"
    )
    preferred_split: Optional[str] = Field(
        default="Auto (Recommended by Coach)",
        description="Preferred workout split (e.g., Push/Pull/Legs, Upper/Lower, Full Body)"
    )


class ExerciseItem(BaseModel):
    """Prescription for a single exercise within a workout."""
    name: str = Field(description="Name of the exercise")
    target_muscle: str = Field(description="Primary muscle group targeted")
    sets: int = Field(description="Number of working sets")
    reps: str = Field(description="Target repetitions or rep range (e.g. '8-10' or '12-15')")
    rpe: Optional[str] = Field(default="RPE 7-8", description="Rate of Perceived Exertion or intensity guidance")
    rest_seconds: int = Field(default=90, description="Rest period between sets in seconds")
    form_cue: Optional[str] = Field(default="", description="Key coaching cue for proper technique")
    alternative: Optional[str] = Field(default="", description="Recommended substitute exercise if equipment is busy")


class WorkoutDay(BaseModel):
    """A single workout session within the weekly plan."""
    day_name: str = Field(description="Name of the day (e.g., 'Day 1: Upper Body Focus' or 'Monday - Push')")
    focus: str = Field(description="Focus area or muscle groups (e.g., 'Chest, Shoulders, Triceps')")
    warmup: List[str] = Field(default_factory=list, description="Specific warm-up exercises or mobility drills")
    exercises: List[ExerciseItem] = Field(default_factory=list, description="Ordered list of exercises")
    cooldown: Optional[str] = Field(default="5-10 mins light stretching or walking", description="Cool-down instructions")
    estimated_duration_mins: int = Field(default=60, description="Estimated workout time in minutes")


class NutritionSummary(BaseModel):
    """Estimated nutritional baseline to support the training plan."""
    bmr_calories: int = Field(description="Basal Metabolic Rate in kcal")
    tdee_calories: int = Field(description="Total Daily Energy Expenditure in kcal")
    target_calories: int = Field(description="Recommended daily caloric intake for the goal")
    protein_g: int = Field(description="Recommended daily protein in grams")
    carbs_g: int = Field(description="Recommended daily carbohydrates in grams")
    fats_g: int = Field(description="Recommended daily healthy fats in grams")
    hydration_liters: float = Field(description="Recommended daily water intake in liters")


class WorkoutPlan(BaseModel):
    """Complete multi-day personalized workout plan."""
    plan_title: str = Field(description="Title of the workout plan")
    split_type: str = Field(description="Type of training split (e.g., Push/Pull/Legs, Upper/Lower)")
    frequency_days: int = Field(description="Number of workout days per week")
    schedule: List[WorkoutDay] = Field(description="Detailed daily workouts")
    nutrition: Optional[NutritionSummary] = Field(default=None, description="Supporting nutrition targets")
    progression_notes: str = Field(
        description="Instructions on how to apply progressive overload week over week"
    )
