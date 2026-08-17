"""Evaluation, security, and safety guardrails for FitForge AI."""

import re
from typing import Dict, Any, List, Optional, Tuple

from src.models import (
    UserProfile,
    WorkoutPlan,
    SafetyAuditResult,
    RiskLevel,
    Gender
)
from src.tools import EXERCISE_DATABASE, verify_exercise_safety
from src.observability import logger


class InputGuardrail:
    """Security and safety guardrail for incoming user prompts and athlete profiles."""

    # Prompt injection patterns
    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
        re.compile(r"system\s*:\s*override", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+(DAN|unrestricted|jailbroken)", re.IGNORECASE),
        re.compile(r"disregard\s+safety\s+guidelines", re.IGNORECASE),
        re.compile(r"pretend\s+you\s+have\s+no\s+rules", re.IGNORECASE)
    ]

    # Extreme / Dangerous health patterns
    UNSAFE_HEALTH_PATTERNS = [
        re.compile(r"\b(anorexia|bulimia|purge|starve\s+myself|500\s*calories\s*a\s*day)\b", re.IGNORECASE),
        re.compile(r"\b(steroid\s*cycle|trenbolone|clenbuterol\s*dosage|dbol\s*cycle)\b", re.IGNORECASE),
        re.compile(r"\b(diagnose\s+my\s+tumor|cure\s+my\s+cancer|prescribe\s+antibiotics)\b", re.IGNORECASE)
    ]

    @classmethod
    def validate_prompt(cls, prompt: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate incoming user message against security and medical safety policies.

        Returns:
            (is_valid, violation_type, remediation_message)
        """
        if not prompt or not prompt.strip():
            return False, "EMPTY_PROMPT", "Please enter a message or question."

        # Check prompt injection
        for pattern in cls.INJECTION_PATTERNS:
            if pattern.search(prompt):
                logger.warning(f"Prompt injection pattern detected: '{prompt[:50]}...'")
                return False, "PROMPT_INJECTION", "I cannot fulfill instructions attempting to override system safety rules."

        # Check unsafe medical / eating disorder queries
        for pattern in cls.UNSAFE_HEALTH_PATTERNS:
            if pattern.search(prompt):
                logger.warning(f"Unsafe health query detected: '{prompt[:50]}...'")
                return (
                    False,
                    "UNSAFE_HEALTH_QUERY",
                    "FitForge AI is an exercise and general fitness coach and cannot provide medical diagnoses, severe caloric starvation guidance, or anabolic drug advice. Please consult a licensed medical professional."
                )

        return True, None, None

    @classmethod
    def validate_profile(cls, profile: UserProfile) -> Tuple[bool, List[str]]:
        """Validate user profile values for basic physical safety bounds."""
        warnings = []
        if profile.age < 16 and profile.days_per_week > 5:
            warnings.append("High training frequency for junior athlete. Recommended: 3-4 days/week.")
        if profile.weight_kg / ((profile.height_cm / 100) ** 2) < 16.0:
            warnings.append("Calculated BMI indicates severely underweight. Prioritize nutritional sufficiency and medical clearance.")
        return len(warnings) == 0, warnings


class OutputGuardrail:
    """Post-generation safety and contraindication verification guardrail."""

    @classmethod
    def audit_plan(
        cls,
        plan: WorkoutPlan,
        profile: UserProfile
    ) -> SafetyAuditResult:
        """
        Audit a generated workout plan against athlete injuries, caloric minimums, and volume safety.
        """
        contraindications = [w.strip().lower() for w in profile.injuries_or_limitations.split() if len(w.strip()) > 2]
        flagged_exercises = []
        modifications_applied = []
        risk_level = RiskLevel.LOW

        # 1. Exercise Contraindication Audit
        if profile.injuries_or_limitations.lower() not in ["none", "no", "n/a"]:
            for day in plan.schedule:
                for ex in day.exercises:
                    safety_check = verify_exercise_safety(ex.name, profile.injuries_or_limitations)
                    if not safety_check["is_safe"]:
                        flagged_exercises.append(f"{day.day_name}: {ex.name} (Conflicts with '{', '.join(safety_check['matched_contraindications'])}')")
                        if safety_check["alternative"]:
                            modifications_applied.append(f"Replace '{ex.name}' with '{safety_check['alternative']}'")
                        risk_level = RiskLevel.HIGH

        # 2. Nutrition Safety Audit
        if plan.nutrition:
            min_calories = 1200 if profile.gender == Gender.FEMALE else 1500
            if plan.nutrition.target_calories < min_calories:
                flagged_exercises.append(f"Caloric intake ({plan.nutrition.target_calories} kcal) is below safe baseline ({min_calories} kcal).")
                modifications_applied.append(f"Clamped target calories to {min_calories} kcal.")
                plan.nutrition.target_calories = min_calories
                risk_level = RiskLevel.MEDIUM

        # 3. Experience vs Intensity Audit
        if profile.experience_level.value.startswith("Beginner"):
            for day in plan.schedule:
                for ex in day.exercises:
                    if ex.rpe and ("RPE 9" in ex.rpe or "RPE 10" in ex.rpe or "Failure" in ex.rpe):
                        flagged_exercises.append(f"Excessive intensity for beginner on '{ex.name}' ({ex.rpe})")
                        ex.rpe = "RPE 7-8"
                        modifications_applied.append(f"Scaled back '{ex.name}' intensity to RPE 7-8 for beginner safety.")
                        if risk_level == RiskLevel.LOW:
                            risk_level = RiskLevel.MEDIUM

        is_safe = (risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]) and (len(flagged_exercises) == 0 or len(modifications_applied) > 0)
        safety_notes = "All exercises verified safe for athlete." if not flagged_exercises else f"Safety adjustments applied: {len(modifications_applied)} modifications."

        return SafetyAuditResult(
            is_safe=is_safe,
            risk_level=risk_level,
            contraindications_checked=contraindications,
            flagged_exercises=flagged_exercises,
            modifications_applied=modifications_applied,
            safety_notes=safety_notes
        )
