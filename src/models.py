"""Data models and schemas for FitForge AI Workout Planning Agent."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


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


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


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

    @field_validator("injuries_or_limitations")
    @classmethod
    def clean_injuries(cls, v: Optional[str]) -> str:
        if not v or not v.strip():
            return "None"
        return v.strip()


class ExerciseItem(BaseModel):
    """Prescription for a single exercise within a workout."""
    name: str = Field(description="Name of the exercise")
    target_muscle: str = Field(description="Primary muscle group targeted")
    sets: int = Field(default=3, ge=1, le=10, description="Number of working sets")
    reps: str = Field(default="8-12", description="Target repetitions or rep range (e.g. '8-10' or '12-15')")
    rpe: Optional[str] = Field(default="RPE 7-8", description="Rate of Perceived Exertion or intensity guidance")
    rest_seconds: int = Field(default=90, ge=15, le=300, description="Rest period between sets in seconds")
    form_cue: Optional[str] = Field(default="", description="Key coaching cue for proper technique")
    alternative: Optional[str] = Field(default="", description="Recommended substitute exercise if equipment is busy or contraindicated")
    tempo: Optional[str] = Field(default="3-0-1-0", description="Lifting tempo (eccentric-pause-concentric-pause)")


class WorkoutDay(BaseModel):
    """A single workout session within the weekly plan."""
    day_name: str = Field(description="Name of the day (e.g., 'Day 1: Upper Body Strength' or 'Push Day')")
    focus: str = Field(description="Focus area or muscle groups (e.g., 'Chest, Shoulders, Triceps')")
    warmup: List[str] = Field(default_factory=list, description="Specific warm-up exercises or mobility drills")
    exercises: List[ExerciseItem] = Field(default_factory=list, description="Ordered list of exercises")
    cooldown: Optional[str] = Field(default="5-10 mins light stretching or walking", description="Cool-down instructions")
    estimated_duration_mins: int = Field(default=60, ge=15, le=180, description="Estimated workout time in minutes")


class NutritionSummary(BaseModel):
    """Estimated nutritional baseline to support the training plan."""
    bmr_calories: int = Field(description="Basal Metabolic Rate in kcal")
    tdee_calories: int = Field(description="Total Daily Energy Expenditure in kcal")
    target_calories: int = Field(description="Recommended daily caloric intake for the goal")
    protein_g: int = Field(description="Recommended daily protein in grams")
    carbs_g: int = Field(description="Recommended daily carbohydrates in grams")
    fats_g: int = Field(description="Recommended daily healthy fats in grams")
    hydration_liters: float = Field(description="Recommended daily water intake in liters")
    dietary_notes: Optional[str] = Field(default="", description="Key meal timing or macronutrient distribution guidance")


class PeriodizationProgression(BaseModel):
    """Periodization and progressive overload strategy."""
    progression_model: str = Field(
        default="Double Progression",
        description="Progression model (e.g., Double Progression, Linear Periodization, Wave Loading)"
    )
    weekly_rules: List[str] = Field(
        default_factory=lambda: [
            "Week 1-3: Add 1 rep per set until top of rep range is hit.",
            "Week 4: Increase load by 2.5-5% and reset to bottom of rep range.",
            "Week 6-8: Deload by reducing volume by 50% at RPE <= 6."
        ],
        description="Week-over-week progression rules"
    )
    deload_strategy: str = Field(
        default="Perform deload every 6-8 weeks reducing sets by 50% and keeping RPE <= 6.",
        description="Deload protocol"
    )


class SafetyAuditResult(BaseModel):
    """Automated safety and contraindication verification result."""
    is_safe: bool = Field(default=True, description="True if no contraindications or safety violations detected")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Assessed risk level")
    contraindications_checked: List[str] = Field(default_factory=list, description="List of injuries or limitations checked")
    flagged_exercises: List[str] = Field(default_factory=list, description="Exercises flagged as potentially risky")
    modifications_applied: List[str] = Field(default_factory=list, description="Modifications or substitutions applied")
    safety_notes: str = Field(default="All prescribed exercises verified safe for athlete profile.", description="Safety summary")


class HITLActionRequest(BaseModel):
    """Human-in-the-Loop pause and approval request for high-stakes actions."""
    requires_approval: bool = Field(default=False, description="True if human confirmation is required")
    action_type: str = Field(default="NONE", description="Type of high-stakes action (e.g., AGGRESSIVE_DEFICIT, MAX_STRAIN_TEST, INJURY_OVERRIDE)")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Severity of the risk")
    description: str = Field(default="", description="Detailed description of the proposed high-stakes action")
    potential_risks: List[str] = Field(default_factory=list, description="Specific risks associated with the action")
    recommended_alternative: str = Field(default="", description="Safer alternative recommendation")
    confirmed_by_user: bool = Field(default=False, description="Whether the user explicitly confirmed the action")


class WorkoutPlan(BaseModel):
    """Complete multi-day personalized workout plan with structured schema."""
    plan_title: str = Field(description="Title of the workout plan")
    split_type: str = Field(description="Type of training split (e.g., Push/Pull/Legs, Upper/Lower)")
    frequency_days: int = Field(description="Number of workout days per week")
    schedule: List[WorkoutDay] = Field(description="Detailed daily workouts")
    nutrition: Optional[NutritionSummary] = Field(default=None, description="Supporting nutrition targets")
    periodization: Optional[PeriodizationProgression] = Field(
        default_factory=PeriodizationProgression,
        description="Progressive overload and periodization details"
    )
    safety_audit: Optional[SafetyAuditResult] = Field(
        default_factory=SafetyAuditResult,
        description="Automated safety audit findings"
    )
    hitl_request: Optional[HITLActionRequest] = Field(
        default=None,
        description="Pending Human-in-the-Loop approval request if high-stakes action detected"
    )


class MemoryFact(BaseModel):
    """Structured fact extracted from athlete conversations for persistent memory."""
    fact_type: str = Field(description="Type of fact (e.g., 'injury', 'preference', 'feedback', 'lift_stat')")
    key: str = Field(description="Identifier or keyword (e.g., 'knee_pain', 'favorite_lift')")
    value: str = Field(description="Fact content or description")
    timestamp: float = Field(description="Unix timestamp when fact was recorded")


class ConversationTurn(BaseModel):
    """Single turn in a persistent conversation history."""
    role: str = Field(description="'user', 'assistant', or 'system'")
    content: str = Field(description="Message text")
    timestamp: float = Field(description="Unix timestamp")
    model: Optional[str] = Field(default=None, description="Model used for generation")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None, description="Recorded tool calls in this turn")
