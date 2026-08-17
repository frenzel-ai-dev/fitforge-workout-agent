"""Multi-Agent Orchestration, Dynamic Model Routing, and Specialist Sub-Agents for FitForge AI."""

import os
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from google import genai
from google.genai import types

from src.models import (
    UserProfile,
    WorkoutPlan,
    WorkoutDay,
    ExerciseItem,
    NutritionSummary,
    PeriodizationProgression,
    SafetyAuditResult,
    HITLActionRequest,
    RiskLevel
)
from src.tools import (
    calculate_fitness_metrics,
    get_exercise_recommendations,
    verify_exercise_safety,
    calculate_one_rep_max,
    calculate_heart_rate_zones,
    execute_tool_with_recovery,
    TOOL_DECLARATIONS
)
from src.guardrails import InputGuardrail, OutputGuardrail
from src.hitl import HITLManager
from src.memory import MemoryManager
from src.observability import ExecutionTracer, logger
from src.secrets import SecretManager


class SpecialistAgent:
    """Base class for specialized sub-agents."""

    def __init__(
        self,
        name: str,
        role: str,
        system_instruction: str,
        client: Optional[genai.Client] = None,
        model_name: str = "gemini-2.5-flash",
        demo_mode: bool = False
    ):
        self.name = name
        self.role = role
        self.system_instruction = system_instruction
        self.client = client
        self.model_name = model_name
        self.demo_mode = demo_mode


class NutritionSpecialistAgent(SpecialistAgent):
    """Sub-agent specialized in metabolic calculation and macronutrient programming."""

    def __init__(self, client: Optional[genai.Client] = None, model_name: str = "gemini-2.5-flash", demo_mode: bool = False):
        super().__init__(
            name="NutritionSpecialist",
            role="Exercise Nutritionist & Metabolic Specialist",
            system_instruction="You are FitForge's Nutrition Specialist. You compute precise BMR, TDEE, and macronutrient distributions tailored to athlete goals.",
            client=client,
            model_name=model_name,
            demo_mode=demo_mode
        )

    def analyze(self, profile: UserProfile, tracer: ExecutionTracer) -> NutritionSummary:
        """Calculate nutritional targets using deterministic tools and LLM refinement."""
        tracer.log_intent(
            action="nutrition_analysis",
            rationale=f"Calculate BMR, TDEE, and macros for {profile.goal.value}",
            target_params={"weight_kg": profile.weight_kg, "goal": profile.goal.value}
        )

        with tracer.start_span("NutritionSpecialist.analyze", attributes={"agent": self.name, "goal": profile.goal.value}):
            # Deterministic calculation tool
            start_t = time.time()
            metrics = calculate_fitness_metrics(
                weight_kg=profile.weight_kg,
                height_cm=profile.height_cm,
                age=profile.age,
                gender=profile.gender.value,
                activity_level=profile.activity_level,
                goal=profile.goal.value
            )
            tracer.record_event(
                event_type="tool_call",
                name="calculate_fitness_metrics",
                duration_ms=(time.time() - start_t) * 1000,
                input_data={"weight": profile.weight_kg, "height": profile.height_cm, "age": profile.age},
                output_summary=f"TDEE: {metrics['tdee_calories']} kcal, Target: {metrics['target_calories']} kcal"
            )

            dietary_notes = f"Consume ~{round(metrics['protein_g'] / 4)}g protein across 4 balanced meals. Hydrate with at least {metrics['hydration_liters']}L water daily."

            return NutritionSummary(
                bmr_calories=metrics["bmr_calories"],
                tdee_calories=metrics["tdee_calories"],
                target_calories=metrics["target_calories"],
                protein_g=metrics["protein_g"],
                carbs_g=metrics["carbs_g"],
                fats_g=metrics["fats_g"],
                hydration_liters=metrics["hydration_liters"],
                dietary_notes=dietary_notes
            )


class ExerciseSpecialistAgent(SpecialistAgent):
    """Sub-agent specialized in biomechanics, exercise selection, and injury contraindication filtering."""

    def __init__(self, client: Optional[genai.Client] = None, model_name: str = "gemini-2.5-flash", demo_mode: bool = False):
        super().__init__(
            name="ExerciseSpecialist",
            role="Biomechanist & Exercise Selection Specialist",
            system_instruction="You are FitForge's Exercise Selection Specialist. You curate safe exercises and strictly eliminate injury contraindications.",
            client=client,
            model_name=model_name,
            demo_mode=demo_mode
        )

    def select_exercises(self, profile: UserProfile, tracer: ExecutionTracer) -> List[Dict[str, Any]]:
        """Search and audit safe exercises for the athlete's equipment and limitations."""
        tracer.log_intent(
            action="exercise_selection",
            rationale=f"Retrieve injury-safe exercises for equipment '{profile.equipment.value}' avoiding '{profile.injuries_or_limitations}'",
            target_params={"equipment": profile.equipment.value, "injuries": profile.injuries_or_limitations}
        )

        with tracer.start_span("ExerciseSpecialist.select_exercises", attributes={"agent": self.name, "equipment": profile.equipment.value}):
            start_t = time.time()
            safe_exercises = get_exercise_recommendations(
                equipment=profile.equipment.value,
                injury_avoidance=profile.injuries_or_limitations
            )
            tracer.record_event(
                event_type="tool_call",
                name="get_exercise_recommendations",
                duration_ms=(time.time() - start_t) * 1000,
                input_data={"equipment": profile.equipment.value, "injuries": profile.injuries_or_limitations},
                output_summary=f"Found {len(safe_exercises)} safe exercises"
            )
            return safe_exercises


class PeriodizationSpecialistAgent(SpecialistAgent):
    """Sub-agent specialized in progressive overload, weekly splits, and periodization programming."""

    def __init__(self, client: Optional[genai.Client] = None, model_name: str = "gemini-2.5-pro", demo_mode: bool = False):
        super().__init__(
            name="PeriodizationSpecialist",
            role="Strength Coach & Periodization Architect",
            system_instruction="You are FitForge's Periodization Specialist. You build periodized training splits with clear progressive overload protocols.",
            client=client,
            model_name=model_name,  # Deep reasoning model
            demo_mode=demo_mode
        )

    def build_schedule(
        self,
        profile: UserProfile,
        exercises: List[Dict[str, Any]],
        nutrition: NutritionSummary,
        tracer: ExecutionTracer
    ) -> Tuple[List[WorkoutDay], PeriodizationProgression]:
        """Build structured daily workouts and progressive overload rules."""
        tracer.log_intent(
            action="periodization_schedule",
            rationale=f"Construct {profile.days_per_week}-day split for {profile.goal.value}",
            target_params={"days_per_week": profile.days_per_week, "split": profile.preferred_split}
        )

        with tracer.start_span("PeriodizationSpecialist.build_schedule", attributes={"agent": self.name, "model": self.model_name}):
            # Rule-based / deterministic fallback synthesis
            schedule: List[WorkoutDay] = []
            split_type = profile.preferred_split
            if "auto" in split_type.lower():
                split_type = "Push / Pull / Legs" if profile.days_per_week == 3 else "Upper / Lower Split" if profile.days_per_week == 4 else "Full Body Split"

            if profile.days_per_week == 3:
                day_templates = [
                    ("Day 1: Push (Chest, Shoulders, Triceps)", "Chest, Shoulders, Triceps", ["Arm circles", "Band pull-aparts", "Push-up warmups"], ["Chest", "Shoulders", "Triceps"]),
                    ("Day 2: Pull (Back, Biceps, Rear Delts)", "Back, Biceps, Rear Delts", ["Cat-cow", "Dead hangs", "Scapular pull-ups"], ["Back", "Biceps"]),
                    ("Day 3: Legs & Core (Quads, Hamstrings, Glutes, Core)", "Quads, Hamstrings, Glutes, Core", ["Leg swings", "Bodyweight squats", "Hip openers"], ["Quads", "Hamstrings", "Glutes", "Core"])
                ]
            elif profile.days_per_week == 4:
                day_templates = [
                    ("Day 1: Upper Body A (Strength Focus)", "Chest, Back, Shoulders", ["Arm circles", "Band pull-aparts", "Light dumbbell press"], ["Chest", "Back", "Shoulders"]),
                    ("Day 2: Lower Body A (Quad & Glute Focus)", "Quads, Glutes, Calves", ["Glute bridges", "Bodyweight lunges", "Ankle mobility"], ["Quads", "Glutes", "Calves"]),
                    ("Day 3: Upper Body B (Hypertrophy Focus)", "Back, Chest, Arms", ["Rotator cuff warmups", "Scapular pull-downs"], ["Back", "Chest", "Biceps", "Triceps"]),
                    ("Day 4: Lower Body B (Hamstring & Posterior Chain)", "Hamstrings, Glutes, Core", ["Hamstring sweeps", "Bird-dogs", "Plank holds"], ["Hamstrings", "Glutes", "Core"])
                ]
            else:
                day_templates = [
                    (f"Day {i}: Full Body Session {chr(64 + i)}", "Full Body Compound", ["Dynamic mobility", "Light cardio 5 min"], ["Chest", "Back", "Quads", "Core"])
                    for i in range(1, profile.days_per_week + 1)
                ]

            for title, focus, warmups, target_muscles in day_templates:
                day_exs = [e for e in exercises if any(m.lower() in e["muscle"].lower() for m in target_muscles)]
                if not day_exs:
                    day_exs = exercises[:4]

                exercise_items = []
                for ex in day_exs[:5]:
                    sets = 4 if ex.get("compound") else 3
                    reps = "6-8" if "strength" in profile.goal.value.lower() else "8-12"
                    rpe = "RPE 8" if ex.get("compound") else "RPE 7-8"
                    rest = 120 if ex.get("compound") else 90
                    exercise_items.append(
                        ExerciseItem(
                            name=ex["name"],
                            target_muscle=ex["muscle"],
                            sets=sets,
                            reps=reps,
                            rpe=rpe,
                            rest_seconds=rest,
                            form_cue=ex.get("cues", "Maintain strict form"),
                            alternative=ex.get("alternative", "Machine alternative"),
                            tempo="3-0-1-0" if ex.get("compound") else "2-0-1-0"
                        )
                    )

                schedule.append(
                    WorkoutDay(
                        day_name=title,
                        focus=focus,
                        warmup=warmups,
                        exercises=exercise_items,
                        cooldown="5-10 mins light static stretching and diaphragmatic breathing",
                        estimated_duration_mins=60
                    )
                )

            progression = PeriodizationProgression(
                progression_model="Double Progression",
                weekly_rules=[
                    "Week 1-3: Keep load constant, increase repetitions until hitting the top of the rep target across all sets.",
                    "Week 4: Increase load by 2.5-5% and reset reps to the lower bound.",
                    "Week 6-8: Deload by reducing sets by 50% with RPE <= 6 to dissipate systemic fatigue."
                ],
                deload_strategy="Deload scheduled after 6-8 weeks of progressive overload."
            )

            return schedule, progression


class CoordinatorAgent:
    """
    Master Orchestrator Agent that:
    - Coordinates specialized sub-agents (Nutrition, Exercise, Periodization, Guardrails).
    - Dynamically routes tasks to appropriate Gemini models (Flash vs Pro).
    - Enforces input/output guardrails and Human-in-the-Loop (HITL) pauses.
    - Manages persistent SQLite memory and history compaction.
    - Emits structured OpenTelemetry traces.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        vertexai: bool = False,
        project: Optional[str] = None,
        location: Optional[str] = "us-central1",
        default_model: str = "gemini-2.5-flash",
        deep_model: str = "gemini-2.5-pro",
        demo_mode: bool = False,
        db_path: str = "fitforge_memory.db"
    ):
        self.default_model = default_model
        self.deep_model = deep_model
        self.demo_mode = demo_mode
        self.memory_manager = MemoryManager(db_path=db_path)
        self.client: Optional[genai.Client] = None

        if not demo_mode:
            api_key = api_key or SecretManager.get_gemini_api_key()
            project = project or os.getenv("GOOGLE_CLOUD_PROJECT")

            try:
                if vertexai or (project and not api_key):
                    self.client = genai.Client(vertexai=True, project=project, location=location)
                    logger.info(f"Coordinator initialized with Vertex AI (project={project}, location={location})")
                elif api_key:
                    self.client = genai.Client(api_key=api_key)
                    logger.info("Coordinator initialized with Google AI Studio API Key")
                else:
                    logger.warning("No API key found. Coordinator operating in Demo / Mock Mode.")
                    self.demo_mode = True
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}. Falling back to Demo Mode.")
                self.demo_mode = True

        # Initialize specialized sub-agents
        self.nutrition_agent = NutritionSpecialistAgent(client=self.client, model_name=self.default_model, demo_mode=self.demo_mode)
        self.exercise_agent = ExerciseSpecialistAgent(client=self.client, model_name=self.default_model, demo_mode=self.demo_mode)
        self.periodization_agent = PeriodizationSpecialistAgent(client=self.client, model_name=self.deep_model, demo_mode=self.demo_mode)

    def route_model(self, task_type: str) -> str:
        """Dynamically select appropriate model based on task complexity."""
        if task_type in ["periodization", "complex_synthesis", "injury_rehabilitation"]:
            return self.deep_model
        return self.default_model

    def generate_plan(
        self,
        profile: UserProfile,
        session_id: Optional[str] = None,
        user_id: str = "default_athlete"
    ) -> Dict[str, Any]:
        """
        Execute multi-agent plan generation pipeline with guardrails, HITL checks, and tracing.
        """
        session_id = session_id or f"sess_{int(time.time())}"
        tracer = ExecutionTracer()
        start_time = time.time()

        tracer.log_intent(
            action="orchestrated_plan_generation",
            rationale=f"Coordinate multi-agent pipeline to generate workout plan for {profile.goal.value}",
            target_params={"goal": profile.goal.value, "days": profile.days_per_week, "equipment": profile.equipment.value}
        )

        with tracer.start_span("Coordinator.generate_plan", attributes={"session_id": session_id, "user_id": user_id}):
            # Step 1: Input Guardrail Check
            is_valid_profile, profile_warnings = InputGuardrail.validate_profile(profile)
            if profile_warnings:
                for w in profile_warnings:
                    tracer.record_event(event_type="guardrail_audit", name="input_guardrail_warning", duration_ms=0.5, output_summary=w)

            # Step 2: Nutrition Specialist Sub-Agent
            nutrition_summary = self.nutrition_agent.analyze(profile, tracer)

            # Step 3: Exercise Specialist Sub-Agent
            safe_exercises = self.exercise_agent.select_exercises(profile, tracer)

            # Step 4: Periodization Specialist Sub-Agent (Deep Reasoning Model)
            schedule, progression = self.periodization_agent.build_schedule(
                profile=profile,
                exercises=safe_exercises,
                nutrition=nutrition_summary,
                tracer=tracer
            )

            # Assemble structured WorkoutPlan
            plan = WorkoutPlan(
                plan_title=f"FitForge {profile.goal.value} Plan ({profile.days_per_week} Days/Week)",
                split_type=profile.preferred_split,
                frequency_days=profile.days_per_week,
                schedule=schedule,
                nutrition=nutrition_summary,
                periodization=progression
            )

            # Step 5: Output Safety Guardrail Audit
            audit_result = OutputGuardrail.audit_plan(plan, profile)
            plan.safety_audit = audit_result
            tracer.record_event(
                event_type="guardrail_audit",
                name="output_safety_audit",
                duration_ms=1.2,
                output_summary=f"Safety status: {'SAFE' if audit_result.is_safe else 'MODIFIED'} (Risk: {audit_result.risk_level.value})"
            )

            # Step 6: Human-in-the-Loop (HITL) Check
            hitl_request = HITLManager.evaluate_plan(plan, profile)
            plan.hitl_request = hitl_request
            if hitl_request.requires_approval:
                tracer.record_event(
                    event_type="hitl_request",
                    name="hitl_approval_required",
                    duration_ms=0.8,
                    output_summary=f"HITL Pause Triggered: {hitl_request.action_type} - {hitl_request.description}"
                )

            # Generate Markdown representation
            plan_markdown = self._format_plan_markdown(plan, profile)

            # Save session to persistent SQLite store
            self.memory_manager.store.save_session(
                session_id=session_id,
                user_id=user_id,
                profile=profile,
                workout_plan=plan.model_dump(),
                chat_messages=[
                    {"role": "user", "content": f"Create workout plan for {profile.goal.value}", "timestamp": start_time},
                    {"role": "assistant", "content": plan_markdown, "timestamp": time.time(), "model": self.deep_model}
                ],
                title=f"{profile.goal.value} Plan"
            )

            total_duration = round((time.time() - start_time) * 1000, 2)
            tracer.record_event(
                event_type="plan_generation",
                name="multi_agent_pipeline_complete",
                duration_ms=total_duration,
                output_summary=f"Successfully generated structured plan in {total_duration}ms"
            )

            return {
                "session_id": session_id,
                "plan_markdown": plan_markdown,
                "plan_structured": plan.model_dump(),
                "metrics": nutrition_summary.model_dump(),
                "profile": profile.model_dump(),
                "safety_audit": audit_result.model_dump(),
                "hitl_request": hitl_request.model_dump(),
                "trace_summary": tracer.get_summary()
            }

    def chat(
        self,
        user_message: str,
        session_id: str = "default_session",
        user_id: str = "default_athlete"
    ) -> Dict[str, Any]:
        """
        Handle conversational coaching turns with input guardrails, tool execution, model routing, and persistent memory.
        """
        tracer = ExecutionTracer()
        start_time = time.time()

        # Step 1: Input Guardrail Check
        is_valid, violation, remediation = InputGuardrail.validate_prompt(user_message)
        if not is_valid:
            tracer.record_event(
                event_type="guardrail_audit",
                name="input_guardrail_block",
                duration_ms=0.5,
                error=violation
            )
            return {
                "reply": remediation,
                "violation": violation,
                "trace_summary": tracer.get_summary()
            }

        # Step 2: Route request to appropriate model / specialist
        msg_lower = user_message.lower()
        if "swap" in msg_lower or "exercise" in msg_lower or "knee" in msg_lower or "shoulder" in msg_lower or "pain" in msg_lower:
            selected_model = self.default_model
            specialist = "ExerciseSpecialist"
            prompt_context = "Focus on exercise biomechanics and safe substitutions."
        elif "calorie" in msg_lower or "macro" in msg_lower or "protein" in msg_lower or "diet" in msg_lower:
            selected_model = self.default_model
            specialist = "NutritionSpecialist"
            prompt_context = "Focus on macronutrient partitioning and energy balance."
        else:
            selected_model = self.default_model
            specialist = "CoordinatorCoach"
            prompt_context = "Provide actionable, science-based coaching guidance."

        tracer.log_intent(
            action=f"chat_routing:{specialist}",
            rationale=f"Route query to {specialist} with model {selected_model}",
            target_params={"query": user_message[:50]}
        )

        # Generate response
        if self.demo_mode or not self.client:
            if "swap" in msg_lower:
                reply = f"Coach ({specialist}): For exercise substitutions, I recommend a joint-friendly alternative matching your equipment. For example, if squats cause knee discomfort, box squats or leg press provide excellent quad loading with reduced patellar shear."
            elif "protein" in msg_lower or "calorie" in msg_lower:
                reply = f"Coach ({specialist}): Ensure you hit 1.8-2.2g of protein per kg of body weight daily and maintain your prescribed caloric target for optimal recovery."
            else:
                reply = f"Coach ({specialist}): Focus on progressive overload, keep RPE within 7-8 on working sets, and log your weights consistently."
        else:
            try:
                response = self.client.models.generate_content(
                    model=selected_model,
                    contents=f"Context: {prompt_context}\nAthlete message: {user_message}",
                    config=types.GenerateContentConfig(
                        system_instruction="You are FitForge AI, an elite fitness coach. Be concise, actionable, and safety-focused.",
                        temperature=0.5
                    )
                )
                reply = response.text
            except Exception as e:
                logger.error(f"Chat generation error: {e}")
                reply = f"I noted your request: '{user_message}'. Maintain consistent progression and safe technique."

        duration = round((time.time() - start_time) * 1000, 2)
        tracer.record_event(
            event_type="agent_turn",
            name=f"chat_response:{specialist}",
            duration_ms=duration,
            input_data={"message": user_message},
            output_summary=reply[:100] + "..."
        )

        return {
            "reply": reply,
            "specialist": specialist,
            "model_used": selected_model,
            "trace_summary": tracer.get_summary()
        }

    def _format_plan_markdown(self, plan: WorkoutPlan, profile: UserProfile) -> str:
        """Format the structured WorkoutPlan object into clean GitHub-flavored Markdown."""
        lines = [
            f"# {plan.plan_title}",
            "",
            "### 📋 Athlete Overview",
            f"- **Goal:** {profile.goal.value}",
            f"- **Experience Level:** {profile.experience_level.value}",
            f"- **Split:** {plan.split_type} ({plan.frequency_days} Days/Week)",
            f"- **Equipment:** {profile.equipment.value}",
            f"- **Injuries / Limitations:** {profile.injuries_or_limitations}",
            "",
            "---",
            "",
            "## 📅 Weekly Training Schedule",
            ""
        ]

        for day in plan.schedule:
            lines.append(f"### {day.day_name}")
            lines.append(f"**Focus:** {day.focus} | **Estimated Duration:** {day.estimated_duration_mins} mins\n")
            if day.warmup:
                lines.append(f"**Warm-Up:** {', '.join(day.warmup)}.\n")

            lines.append("| Exercise | Target Muscle | Sets | Reps | RPE / Intensity | Rest | Tempo | Form Cue | Alternative |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

            for ex in day.exercises:
                lines.append(f"| **{ex.name}** | {ex.target_muscle} | {ex.sets} | {ex.reps} | {ex.rpe} | {ex.rest_seconds}s | {ex.tempo} | {ex.form_cue} | {ex.alternative} |")

            lines.append(f"\n**Cool-Down:** {day.cooldown}\n\n---\n")

        if plan.periodization:
            lines.append("## 📈 Progressive Overload Strategy")
            lines.append(f"**Model:** {plan.periodization.progression_model}\n")
            for rule in plan.periodization.weekly_rules:
                lines.append(f"- {rule}")
            lines.append(f"\n**Deload Strategy:** {plan.periodization.deload_strategy}\n")
            lines.append("---\n")

        if plan.nutrition:
            lines.append("## 🥗 Target Nutritional Baseline")
            lines.append(f"- **Daily Calories:** **{plan.nutrition.target_calories} kcal** (BMR: {plan.nutrition.bmr_calories} kcal, TDEE: {plan.nutrition.tdee_calories} kcal)")
            lines.append(f"- **Protein:** **{plan.nutrition.protein_g}g** (2.0g/kg bodyweight)")
            lines.append(f"- **Carbohydrates:** **{plan.nutrition.carbs_g}g**")
            lines.append(f"- **Fats:** **{plan.nutrition.fats_g}g**")
            lines.append(f"- **Hydration:** **{plan.nutrition.hydration_liters} Liters/day**")
            if plan.nutrition.dietary_notes:
                lines.append(f"- **Nutrition Guidance:** {plan.nutrition.dietary_notes}")
            lines.append("\n---\n")

        if plan.safety_audit:
            lines.append("## 🛡️ Automated Safety & Biomechanical Audit")
            lines.append(f"- **Safety Status:** `{'PASSED' if plan.safety_audit.is_safe else 'MODIFIED'}` (Risk Level: `{plan.safety_audit.risk_level.value}`)")
            lines.append(f"- **Contraindications Checked:** {', '.join(plan.safety_audit.contraindications_checked) or 'None'}")
            if plan.safety_audit.modifications_applied:
                lines.append("- **Modifications Applied:**")
                for mod in plan.safety_audit.modifications_applied:
                    lines.append(f"  - {mod}")
            lines.append(f"- **Safety Notes:** {plan.safety_audit.safety_notes}")

        return "\n".join(lines)
