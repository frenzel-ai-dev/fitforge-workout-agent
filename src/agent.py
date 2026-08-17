"""Workout Planning Agent powered by Gemini / Vertex AI and deterministic fitness tools."""

import os
import json
import time
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from src.models import UserProfile, WorkoutPlan, WorkoutDay, ExerciseItem, NutritionSummary
from src.tools import calculate_fitness_metrics, get_exercise_recommendations
from src.observability import ExecutionTracer, logger


SYSTEM_INSTRUCTION = """You are FitForge AI, an elite personal trainer, exercise physiologist, and strength coach.
Your mission is to design safe, science-backed, highly customized workout routines and provide practical coaching advice.

Core Principles:
1. Prioritize safety: Never prescribe exercises contraindicated by user injuries. Provide clear form cues and substitute options.
2. Progressive Overload: Ensure weekly progression mechanisms (rep ranges, RPE targets, weight increases) are clearly defined.
3. Specificity & Practicality: Fit the routine strictly to the athlete's equipment, schedule, and experience level.
4. Professional & Encouraging: Provide concise, clear, and actionable feedback.
"""


class WorkoutAgent:
    """Agent that orchestrates fitness tools and LLM reasoning to build personalized workout plans."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        vertexai: bool = False,
        project: Optional[str] = None,
        location: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
        demo_mode: bool = False
    ):
        self.model_name = model_name
        self.demo_mode = demo_mode
        self.tracer = ExecutionTracer()
        self.chat_history: List[Dict[str, str]] = []
        self.client: Optional[genai.Client] = None

        if not demo_mode:
            # Check environment variables if not provided
            api_key = api_key or os.getenv("GEMINI_API_KEY")
            project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
            location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

            try:
                if vertexai or (project and not api_key):
                    self.client = genai.Client(vertexai=True, project=project, location=location)
                    logger.info(f"Initialized WorkoutAgent with Vertex AI (project={project}, location={location})")
                elif api_key:
                    self.client = genai.Client(api_key=api_key)
                    logger.info("Initialized WorkoutAgent with Google AI Studio API Key")
                else:
                    logger.warning("No API key or Vertex AI config found. Falling back to Demo Mode.")
                    self.demo_mode = True
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}. Falling back to Demo Mode.")
                self.demo_mode = True

    def generate_plan(self, profile: UserProfile) -> Dict[str, Any]:
        """
        Generate a complete workout plan and nutrition targets for the given user profile.

        Args:
            profile: UserProfile containing goals, biometrics, equipment, and injuries.

        Returns:
            Dictionary containing markdown plan, structured data, and nutrition summary.
        """
        start_time = time.time()

        # Step 1: Execute deterministic fitness metric calculation tool
        tool_start = time.time()
        metrics = calculate_fitness_metrics(
            weight_kg=profile.weight_kg,
            height_cm=profile.height_cm,
            age=profile.age,
            gender=profile.gender.value,
            activity_level=profile.activity_level,
            goal=profile.goal.value
        )
        self.tracer.record_event(
            event_type="tool_call",
            name="calculate_fitness_metrics",
            duration_ms=(time.time() - tool_start) * 1000,
            input_data={"weight_kg": profile.weight_kg, "goal": profile.goal.value},
            output_summary=f"TDEE: {metrics['tdee_calories']} kcal, Target: {metrics['target_calories']} kcal"
        )

        # Step 2: Execute exercise recommendations lookup tool
        tool_start = time.time()
        recommended_exercises = get_exercise_recommendations(
            equipment=profile.equipment.value,
            injury_avoidance=profile.injuries_or_limitations
        )
        self.tracer.record_event(
            event_type="tool_call",
            name="get_exercise_recommendations",
            duration_ms=(time.time() - tool_start) * 1000,
            input_data={"equipment": profile.equipment.value, "injuries": profile.injuries_or_limitations},
            output_summary=f"Found {len(recommended_exercises)} safe matching exercises"
        )

        # Step 3: Generate plan with Gemini LLM or Demo fallback
        if self.demo_mode or not self.client:
            plan_markdown = self._generate_rule_based_plan(profile, metrics, recommended_exercises)
        else:
            plan_markdown = self._generate_llm_plan(profile, metrics, recommended_exercises)

        total_duration = (time.time() - start_time) * 1000
        self.tracer.record_event(
            event_type="plan_generation",
            name="generate_plan",
            duration_ms=total_duration,
            output_summary=f"Generated workout plan for {profile.goal.value}"
        )

        # Seed chat history with the generated plan
        self.chat_history = [
            {"role": "user", "content": f"Please create a workout plan for: {profile.model_dump_json()}"},
            {"role": "assistant", "content": plan_markdown}
        ]

        return {
            "plan_markdown": plan_markdown,
            "metrics": metrics,
            "profile": profile.model_dump(),
            "trace_summary": self.tracer.get_summary()
        }

    def _generate_llm_plan(
        self,
        profile: UserProfile,
        metrics: Dict[str, Any],
        exercises: List[Dict[str, Any]]
    ) -> str:
        """Call Gemini to synthesize a structured workout plan."""
        prompt = f"""
Create a highly structured, professional {profile.days_per_week}-day weekly workout routine for the following athlete:

Athlete Profile:
- Goal: {profile.goal.value}
- Experience Level: {profile.experience_level.value}
- Training Frequency: {profile.days_per_week} days/week
- Available Equipment: {profile.equipment.value}
- Injuries / Limitations to AVOID: {profile.injuries_or_limitations}
- Preferred Split: {profile.preferred_split}

Calculated Nutritional Baseline:
- Target Calories: {metrics['target_calories']} kcal/day (BMR: {metrics['bmr_calories']}, TDEE: {metrics['tdee_calories']})
- Protein: {metrics['protein_g']}g | Carbs: {metrics['carbs_g']}g | Fats: {metrics['fats_g']}g | Hydration: {metrics['hydration_liters']}L/day

Available Injury-Safe Exercises to Pick From:
{json.dumps(exercises[:20], indent=2)}

Please format the response in clean Markdown with the following structure:
1. # Plan Overview (Title, Split Type, Frequency, Focus)
2. ## Daily Schedule (For each training day: Day Name, Muscle Focus, Warm-Up, Exercise Table [Exercise, Sets, Reps, RPE, Rest, Form Cue, Alternative], Cool-Down)
3. ## Progressive Overload Strategy (Week-over-week progression rules)
4. ## Nutrition & Recovery Guidelines (Calories, macros, hydration, sleep advice)
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.4
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}. Using fallback generator.")
            return self._generate_rule_based_plan(profile, metrics, exercises)

    def _generate_rule_based_plan(
        self,
        profile: UserProfile,
        metrics: Dict[str, Any],
        exercises: List[Dict[str, Any]]
    ) -> str:
        """Deterministic rule-based generator used for demo/testing mode."""
        split_name = "Push / Pull / Legs" if profile.days_per_week == 3 else "Upper / Lower Split" if profile.days_per_week == 4 else "Full Body Split"

        plan = f"""# FitForge Customized Workout Plan

### 📋 Overview
- **Goal:** {profile.goal.value}
- **Experience Level:** {profile.experience_level.value}
- **Split Type:** {split_name} ({profile.days_per_week} Days/Week)
- **Equipment:** {profile.equipment.value}
- **Injury Safeguards:** {profile.injuries_or_limitations}

---

## 📅 Weekly Schedule

"""
        days = []
        if profile.days_per_week == 3:
            days = [
                ("Day 1: Push (Chest, Shoulders, Triceps)", ["Chest", "Shoulders", "Triceps"]),
                ("Day 2: Pull (Back, Rear Delts, Biceps)", ["Back", "Biceps"]),
                ("Day 3: Legs & Core (Quads, Hamstrings, Glutes, Core)", ["Quads", "Hamstrings", "Glutes", "Core"])
            ]
        elif profile.days_per_week == 4:
            days = [
                ("Day 1: Upper Body A (Strength Focus)", ["Chest", "Back", "Shoulders"]),
                ("Day 2: Lower Body A (Quad & Glute Focus)", ["Quads", "Glutes", "Core"]),
                ("Day 3: Upper Body B (Hypertrophy Focus)", ["Back", "Chest", "Biceps", "Triceps"]),
                ("Day 4: Lower Body B (Hamstring & Posterior Focus)", ["Hamstrings", "Quads", "Calves", "Core"])
            ]
        else:
            for i in range(1, profile.days_per_week + 1):
                days.append((f"Day {i}: Full Body Session {chr(64 + i)}", ["Chest", "Back", "Quads", "Core"]))

        for day_title, muscles in days:
            plan += f"### {day_title}\n"
            plan += "**Warm-Up:** 5 mins dynamic mobility (arm circles, leg swings, cat-cow, bodyweight squats).\n\n"
            plan += "| Exercise | Target Muscle | Sets | Reps | Intensity / RPE | Rest | Key Cue |\n"
            plan += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"

            day_exs = [e for e in exercises if any(m.lower() in e["muscle"].lower() for m in muscles)]
            if not day_exs:
                day_exs = exercises[:4]

            for ex in day_exs[:5]:
                sets = 4 if ex.get("compound") else 3
                reps = "6-8" if "strength" in profile.goal.value.lower() else "8-12"
                rpe = "RPE 8" if ex.get("compound") else "RPE 7-8"
                rest = "120s" if ex.get("compound") else "60-90s"
                plan += f"| **{ex['name']}** | {ex['muscle']} | {sets} | {reps} | {rpe} | {rest} | {ex.get('cues', 'Controlled tempo')} |\n"

            plan += "\n**Cool-Down:** 5 mins light static stretching and deep diaphragmatic breathing.\n\n---\n\n"

        plan += f"""## 📈 Progressive Overload Strategy
1. **Double Progression:** Aim for the top of the rep range (e.g., 12 reps) across all sets with good form.
2. **Load Increase:** Once achieved, increase weight by 2-5% (1-2.5 kg for dumbbells/cables, 2.5-5 kg for barbells) and reset to the bottom rep target (8 reps).
3. **Deload Week:** Every 6-8 weeks, reduce working sets by 50% and keep RPE ≤ 6 to facilitate systemic recovery.

---

## 🥗 Nutrition & Recovery Baseline
- **Daily Target Calories:** **{metrics['target_calories']} kcal** (BMR: {metrics['bmr_calories']} kcal, TDEE: {metrics['tdee_calories']} kcal)
- **Macronutrients:**
  - 🥩 **Protein:** **{metrics['protein_g']}g** (2.0g/kg bodyweight for muscle repair & growth)
  - 🍚 **Carbohydrates:** **{metrics['carbs_g']}g** (Primary glycogen fuel for intense workouts)
  - 🥑 **Fats:** **{metrics['fats_g']}g** (Hormonal support and joint health)
- 💧 **Hydration Target:** **{metrics['hydration_liters']} Liters/day**
- 😴 **Sleep & Recovery:** 7.5 - 9 hours of quality sleep nightly.
"""
        return plan

    def chat(self, user_message: str) -> str:
        """
        Continue the coaching conversation to answer questions or modify the plan.

        Args:
            user_message: User query or tweak request (e.g., 'Swap squats for leg press').

        Returns:
            Coach's response.
        """
        start_time = time.time()
        self.chat_history.append({"role": "user", "content": user_message})

        if self.demo_mode or not self.client:
            # Deterministic response for demo/mock mode
            reply = f"Coach Response: I've noted your request ('{user_message}'). "
            if "swap" in user_message.lower() or "substitute" in user_message.lower():
                reply += "I recommend replacing the movement with an alternative from our exercise database that matches your equipment and avoids joint strain."
            elif "calorie" in user_message.lower() or "protein" in user_message.lower():
                reply += "Keep your daily protein target consistent at ~2.0g per kg of body weight to support muscle recovery."
            else:
                reply += "Make sure to maintain proper form, log your weights, and stay consistent with the progressive overload guidelines."
        else:
            try:
                # Format conversation history for Gemini
                contents = []
                for msg in self.chat_history:
                    role = "user" if msg["role"] == "user" else "model"
                    contents.append(types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["content"])]
                    ))

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.5
                    )
                )
                reply = response.text
            except Exception as e:
                logger.error(f"Chat generation error: {e}")
                reply = f"I encountered an issue processing your request: {e}. Please try again."

        self.chat_history.append({"role": "assistant", "content": reply})
        duration = (time.time() - start_time) * 1000
        self.tracer.record_event(
            event_type="agent_turn",
            name="chat",
            duration_ms=duration,
            input_data={"message": user_message},
            output_summary=reply[:100] + "..." if len(reply) > 100 else reply
        )
        return reply
