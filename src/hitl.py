"""Human-in-the-Loop (HITL) pause and approval manager for high-stakes fitness actions."""

from typing import Optional, List
from src.models import (
    UserProfile,
    WorkoutPlan,
    HITLActionRequest,
    RiskLevel
)
from src.observability import logger


class HITLManager:
    """
    Identifies high-stakes fitness and nutrition recommendations that require
    explicit athlete/human review and confirmation before finalizing.
    """

    @classmethod
    def evaluate_plan(
        cls,
        plan: WorkoutPlan,
        profile: UserProfile
    ) -> HITLActionRequest:
        """
        Evaluate if a workout plan contains high-stakes parameters requiring user sign-off.
        """
        injuries_lower = (profile.injuries_or_limitations or "").lower()
        has_injuries = injuries_lower not in ["none", "no", "n/a", ""]

        # 1. High-Stakes Deficit Check (> 750 kcal/day deficit)
        if plan.nutrition:
            deficit = plan.nutrition.tdee_calories - plan.nutrition.target_calories
            if deficit >= 750:
                logger.warning(f"HITL Triggered: Aggressive caloric deficit ({deficit} kcal/day)")
                return HITLActionRequest(
                    requires_approval=True,
                    action_type="AGGRESSIVE_CALORIC_DEFICIT",
                    risk_level=RiskLevel.HIGH,
                    description=f"The proposed plan prescribes an aggressive caloric deficit of {deficit} kcal/day (Target: {plan.nutrition.target_calories} kcal vs TDEE: {plan.nutrition.tdee_calories} kcal).",
                    potential_risks=[
                        "Accelerated loss of lean muscle mass",
                        "Elevated training fatigue and impaired recovery",
                        "Hormonal and metabolic down-regulation"
                    ],
                    recommended_alternative=f"A moderate deficit of 300-500 kcal/day (Target: ~{plan.nutrition.tdee_calories - 400} kcal) is recommended for sustainable fat loss."
                )

        # 2. High-Stakes 1RM / High-Strain Compound Lift with Prior Injury Check
        if has_injuries:
            high_strain_exercises = ["barbell back squat", "barbell bent-over row", "overhead barbell press", "romanian deadlift"]
            for day in plan.schedule:
                for ex in day.exercises:
                    ex_name = ex.name.lower()
                    if any(hse in ex_name for hse in high_strain_exercises):
                        if any(inj in injuries_lower for inj in ["knee", "back", "lumbar", "spine", "disc", "rotator cuff"]):
                            logger.warning(f"HITL Triggered: High-strain exercise '{ex.name}' with injury '{profile.injuries_or_limitations}'")
                            return HITLActionRequest(
                                requires_approval=True,
                                action_type="HIGH_STRAIN_LIFT_WITH_INJURY",
                                risk_level=RiskLevel.HIGH,
                                description=f"The plan includes '{ex.name}', which imposes high axial or joint load given your reported '{profile.injuries_or_limitations}'.",
                                potential_risks=[
                                    f"Aggravation of existing {profile.injuries_or_limitations}",
                                    "Increased injury recurrence risk under heavy load"
                                ],
                                recommended_alternative=f"Substitute '{ex.name}' with '{ex.alternative or 'a machine or chest-supported alternative'}'."
                            )

        # 3. Very High Training Frequency for Beginners
        if profile.experience_level.value.startswith("Beginner") and profile.days_per_week >= 6:
            return HITLActionRequest(
                requires_approval=True,
                action_type="HIGH_VOLUME_BEGINNER",
                risk_level=RiskLevel.MEDIUM,
                description=f"A training frequency of {profile.days_per_week} days/week is very demanding for a beginner lifter.",
                potential_risks=[
                    "Systemic overreaching and central nervous system fatigue",
                    "Joint and connective tissue overuse injuries"
                ],
                recommended_alternative="Start with 3 to 4 days/week to build foundational work capacity."
            )

        # No HITL pause required
        return HITLActionRequest(
            requires_approval=False,
            action_type="NONE",
            risk_level=RiskLevel.LOW,
            description="Routine passes all automated safety criteria."
        )
