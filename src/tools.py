"""Deterministic calculation and exercise lookup tools for the Workout Planning Agent."""

import math
from typing import Dict, List, Any, Optional

# Curated exercise database with categories, equipment, and injury contraindications
EXERCISE_DATABASE = [
    # Chest
    {"name": "Barbell Bench Press", "muscle": "Chest", "equipment": "Barbell", "compound": True, "contraindications": ["shoulder impingement", "rotator cuff", "shoulder pain"], "cues": "Retract scapulae, touch lower sternum, drive through feet.", "alternative": "Dumbbell Flat Bench Press"},
    {"name": "Incline Dumbbell Press", "muscle": "Chest", "equipment": "Dumbbell", "compound": True, "contraindications": ["shoulder pain", "shoulder impingement"], "cues": "30-degree incline, control descent, press upward without clinking weights.", "alternative": "Incline Cable Press"},
    {"name": "Push-Ups", "muscle": "Chest", "equipment": "Bodyweight", "compound": True, "contraindications": ["wrist pain"], "cues": "Core tight, glutes engaged, elbows at 45 degrees.", "alternative": "Incline Push-Ups / Knee Push-Ups"},
    {"name": "Cable Chest Flyes", "muscle": "Chest", "equipment": "Cable", "compound": False, "contraindications": ["shoulder instability"], "cues": "Slight elbow bend, focus on chest squeeze at peak contraction.", "alternative": "Dumbbell Flyes"},
    {"name": "Chest Press Machine", "muscle": "Chest", "equipment": "Machine", "compound": True, "contraindications": [], "cues": "Handles at mid-chest level, smooth tempo, don't lock elbows.", "alternative": "Dumbbell Bench Press"},

    # Back
    {"name": "Barbell Bent-Over Row", "muscle": "Back", "equipment": "Barbell", "compound": True, "contraindications": ["lower back pain", "lumbar herniation", "back injury"], "cues": "Hinge hips back, brace core, pull bar to lower ribcage.", "alternative": "Chest-Supported Dumbbell Row"},
    {"name": "Lat Pulldown", "muscle": "Back", "equipment": "Cable", "compound": True, "contraindications": [], "cues": "Pull elbows down into back pockets, slight torso lean.", "alternative": "Pull-Ups / Band Lat Pulldowns"},
    {"name": "Pull-Ups / Chin-Ups", "muscle": "Back", "equipment": "Bodyweight", "compound": True, "contraindications": ["shoulder impingement", "elbow tendonitis"], "cues": "Full dead hang at bottom, drive chest to bar.", "alternative": "Lat Pulldown / Inverted Row"},
    {"name": "Seated Cable Row", "muscle": "Back", "equipment": "Cable", "compound": True, "contraindications": [], "cues": "Maintain tall neutral spine, squeeze shoulder blades together.", "alternative": "One-Arm Dumbbell Row"},
    {"name": "Chest-Supported Dumbbell Row", "muscle": "Back", "equipment": "Dumbbell", "compound": True, "contraindications": [], "cues": "Chest on 45-degree incline bench, zero lumbar strain.", "alternative": "Seated Cable Row"},

    # Shoulders
    {"name": "Overhead Barbell Press", "muscle": "Shoulders", "equipment": "Barbell", "compound": True, "contraindications": ["shoulder impingement", "lower back pain", "rotator cuff"], "cues": "Brace core, glutes tight, press straight overhead.", "alternative": "Seated Dumbbell Shoulder Press"},
    {"name": "Seated Dumbbell Shoulder Press", "muscle": "Shoulders", "equipment": "Dumbbell", "compound": True, "contraindications": ["shoulder impingement", "shoulder pain"], "cues": "Palms slightly angled inward (scapular plane), press without arching back.", "alternative": "Machine Shoulder Press"},
    {"name": "Dumbbell Lateral Raise", "muscle": "Shoulders", "equipment": "Dumbbell", "compound": False, "contraindications": [], "cues": "Lead with elbows, slight forward lean, pour the pitcher motion.", "alternative": "Cable Lateral Raise"},
    {"name": "Face Pulls", "muscle": "Shoulders", "equipment": "Cable", "compound": False, "contraindications": [], "cues": "Rope attachment to eye level, external rotation of shoulders.", "alternative": "Rear Delt Dumbbell Flyes"},
    {"name": "Pike Push-Ups", "muscle": "Shoulders", "equipment": "Bodyweight", "compound": True, "contraindications": ["wrist pain", "shoulder pain"], "cues": "Hips high in V-shape, lower head diagonally forward.", "alternative": "Decline Push-Ups"},

    # Legs (Quads & Calves)
    {"name": "Barbell Back Squat", "muscle": "Quads", "equipment": "Barbell", "compound": True, "contraindications": ["knee pain", "patellar tendonitis", "lower back pain", "knee injury"], "cues": "Spread the floor, break at hips and knees simultaneously, chest upright.", "alternative": "Goblet Squat / Leg Press"},
    {"name": "Goblet Box Squat", "muscle": "Quads", "equipment": "Dumbbell", "compound": True, "contraindications": [], "cues": "Hold dumbbell at chest, sit back onto box, knees track over toes.", "alternative": "Bodyweight Box Squats"},
    {"name": "Leg Press Machine", "muscle": "Quads", "equipment": "Machine", "compound": True, "contraindications": ["lower back pain (if rounding)"], "cues": "Feet hip-width on platform, control eccentric, avoid knee cave.", "alternative": "Goblet Squats"},
    {"name": "Bulgarian Split Squat", "muscle": "Quads", "equipment": "Dumbbell", "compound": True, "contraindications": ["knee pain", "patellar tendonitis"], "cues": "Rear foot on bench, descend straight down, forward torso lean for glute focus.", "alternative": "Reverse Lunges"},
    {"name": "Bodyweight Air Squats", "muscle": "Quads", "equipment": "Bodyweight", "compound": True, "contraindications": [], "cues": "Weight evenly across whole foot, reach depth below parallel.", "alternative": "Assisted Chair Squats"},
    {"name": "Standing Calf Raise", "muscle": "Calves", "equipment": "Dumbbell", "compound": False, "contraindications": ["achilles tendonitis"], "cues": "Full stretch at bottom, 2-second pause at peak contraction.", "alternative": "Seated Calf Raise"},

    # Legs (Hamstrings & Glutes)
    {"name": "Romanian Deadlift (RDL)", "muscle": "Hamstrings/Glutes", "equipment": "Barbell", "compound": True, "contraindications": ["acute lower back pain", "lumbar herniation", "back injury"], "cues": "Soft knee bend, push hips directly backward, feel hamstring stretch.", "alternative": "Dumbbell RDL / Single-Leg RDL"},
    {"name": "Dumbbell Romanian Deadlift", "muscle": "Hamstrings/Glutes", "equipment": "Dumbbell", "compound": True, "contraindications": [], "cues": "Keep dumbbells close to shins, flat back, squeeze glutes at top.", "alternative": "Glute Bridges"},
    {"name": "Lying / Seated Leg Curl", "muscle": "Hamstrings", "equipment": "Machine", "compound": False, "contraindications": [], "cues": "Dorsiflex ankles, smooth contraction, 3-second negative.", "alternative": "Swiss Ball Leg Curls / Nordic Curls"},
    {"name": "Barbell Hip Thrust", "muscle": "Glutes", "equipment": "Barbell", "compound": True, "contraindications": [], "cues": "Upper back against bench, drive through heels, posterior pelvic tilt at top.", "alternative": "Dumbbell Glute Bridge"},
    {"name": "Glute Bridge (Bodyweight / Banded)", "muscle": "Glutes", "equipment": "Bodyweight", "compound": False, "contraindications": [], "cues": "Tuck chin, squeeze glutes hard for 2 seconds at the top.", "alternative": "Single-Leg Glute Bridge"},

    # Arms (Biceps & Triceps)
    {"name": "Incline Dumbbell Bicep Curl", "muscle": "Biceps", "equipment": "Dumbbell", "compound": False, "contraindications": ["bicep tendonitis"], "cues": "45-degree bench, full stretch at bottom, supinate wrists.", "alternative": "Standing Hammer Curl"},
    {"name": "Dumbbell Hammer Curl", "muscle": "Biceps", "equipment": "Dumbbell", "compound": False, "contraindications": [], "cues": "Neutral grip, targets brachialis and forearms, strict form.", "alternative": "Cable Rope Hammer Curl"},
    {"name": "Tricep Rope Pushdown", "muscle": "Triceps", "equipment": "Cable", "compound": False, "contraindications": ["elbow tendonitis"], "cues": "Elbows pinned to sides, spread rope at bottom contraction.", "alternative": "Dumbbell Overhead Tricep Extension"},
    {"name": "Dumbbell Overhead Tricep Extension", "muscle": "Triceps", "equipment": "Dumbbell", "compound": False, "contraindications": ["elbow pain"], "cues": "Elbows pointed forward, deep stretch in long head of triceps.", "alternative": "Bench Dips / Tricep Kickbacks"},
    {"name": "Parallel Bar Dips / Bench Dips", "muscle": "Triceps", "equipment": "Bodyweight", "compound": True, "contraindications": ["shoulder instability", "shoulder pain"], "cues": "Torso upright for triceps, lower to 90 degrees.", "alternative": "Close-Grip Push-Ups"},

    # Core & Functional
    {"name": "Hanging Knee / Leg Raise", "muscle": "Core", "equipment": "Bodyweight", "compound": False, "contraindications": ["shoulder pain", "shoulder impingement"], "cues": "Avoid swinging, curl pelvis upward toward chest.", "alternative": "Lying Leg Raise / Deadbugs"},
    {"name": "Abdominal Plank", "muscle": "Core", "equipment": "Bodyweight", "compound": False, "contraindications": [], "cues": "Glutes squeezed, forearms pressing floor away, neutral spine.", "alternative": "Bird Dog / Deadbugs"},
    {"name": "Cable Woodchoppers", "muscle": "Core", "equipment": "Cable", "compound": False, "contraindications": ["acute lower back disc issues", "lower back pain"], "cues": "Rotate from thoracic spine and hips, keep arms extended.", "alternative": "Bicycle Crunches"}
]


def calculate_fitness_metrics(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str = "Male",
    activity_level: str = "Moderately Active (exercise 3-5 days/wk)",
    goal: str = "Hypertrophy (Muscle Gain)"
) -> Dict[str, Any]:
    """
    Calculate BMR (Mifflin-St Jeor), TDEE, target caloric intake, macronutrients, and hydration.

    Args:
        weight_kg: Athlete body weight in kilograms (30.0 to 300.0).
        height_cm: Athlete height in centimeters (100.0 to 250.0).
        age: Age in years (14 to 100).
        gender: Athlete gender ('Male', 'Female', 'Other').
        activity_level: Activity multiplier descriptor.
        goal: Target fitness goal.

    Returns:
        Dictionary containing BMR, TDEE, target calories, protein, carbs, fats, and hydration targets.
    """
    # Validation / Boundary check
    if not (30.0 <= weight_kg <= 300.0):
        raise ValueError(f"Weight ({weight_kg} kg) must be between 30.0 kg and 300.0 kg.")
    if not (100.0 <= height_cm <= 250.0):
        raise ValueError(f"Height ({height_cm} cm) must be between 100.0 cm and 250.0 cm.")
    if not (14 <= age <= 100):
        raise ValueError(f"Age ({age}) must be between 14 and 100 years.")

    # 1. BMR Calculation (Mifflin-St Jeor)
    if "female" in gender.lower():
        bmr = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age) - 161.0
    else:  # Male or default
        bmr = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age) + 5.0

    bmr = round(bmr)

    # 2. Activity Multiplier
    activity_lower = activity_level.lower()
    if "sedentary" in activity_lower:
        multiplier = 1.2
    elif "light" in activity_lower:
        multiplier = 1.375
    elif "very" in activity_lower:
        multiplier = 1.725
    elif "extreme" in activity_lower:
        multiplier = 1.9
    else:  # Moderately active (default)
        multiplier = 1.55

    tdee = round(bmr * multiplier)

    # 3. Caloric Adjustment based on goal
    goal_lower = goal.lower()
    if "hypertrophy" in goal_lower or "muscle" in goal_lower:
        target_calories = tdee + 300  # Lean bulk
    elif "fat loss" in goal_lower or "cut" in goal_lower:
        target_calories = max(1200, tdee - 500)  # Moderate deficit
    elif "strength" in goal_lower or "power" in goal_lower:
        target_calories = tdee + 150  # Slight surplus
    else:
        target_calories = tdee  # Maintenance

    # 4. Macronutrient Partitioning
    # Protein: 2.0g per kg of bodyweight
    protein_g = round(weight_kg * 2.0)
    protein_cals = protein_g * 4

    # Fats: 25% of total calories (min 0.7g/kg)
    fat_cals = target_calories * 0.25
    fat_g = max(round(weight_kg * 0.8), round(fat_cals / 9))
    actual_fat_cals = fat_g * 9

    # Carbs: Remaining calories
    remaining_cals = max(0, target_calories - protein_cals - actual_fat_cals)
    carbs_g = round(remaining_cals / 4)

    # Hydration: 35ml/kg + 0.75L for training
    hydration_liters = round((weight_kg * 0.035) + 0.75, 1)

    return {
        "status": "success",
        "bmr_calories": int(bmr),
        "tdee_calories": int(tdee),
        "target_calories": int(target_calories),
        "protein_g": int(protein_g),
        "carbs_g": int(carbs_g),
        "fats_g": int(fat_g),
        "hydration_liters": float(hydration_liters),
        "goal_applied": goal,
        "calculation_method": "Mifflin-St Jeor + Macro Partitioning"
    }


def calculate_one_rep_max(weight: float, reps: int) -> Dict[str, Any]:
    """
    Calculate estimated 1RM using Epley and Brzycki equations.

    Args:
        weight: Weight lifted (kg or lbs). Must be > 0.
        reps: Number of repetitions completed (1-12).

    Returns:
        Estimated 1RM and percentage training load recommendations.
    """
    if weight <= 0:
        raise ValueError(f"Weight ({weight}) must be greater than 0.")
    if reps < 1 or reps > 30:
        raise ValueError(f"Reps ({reps}) must be between 1 and 30.")

    if reps == 1:
        estimated_1rm = weight
    else:
        epley = weight * (1.0 + reps / 30.0)
        brzycki = weight * (36.0 / (37.0 - reps)) if reps < 37 else epley
        estimated_1rm = (epley + brzycki) / 2.0

    one_rm = round(estimated_1rm, 1)
    return {
        "status": "success",
        "estimated_1rm": one_rm,
        "input_weight": weight,
        "input_reps": reps,
        "zones": {
            "strength_85_90%": f"{round(one_rm * 0.85, 1)} - {round(one_rm * 0.90, 1)} (3-5 reps)",
            "hypertrophy_70_80%": f"{round(one_rm * 0.70, 1)} - {round(one_rm * 0.80, 1)} (8-12 reps)",
            "endurance_55_65%": f"{round(one_rm * 0.55, 1)} - {round(one_rm * 0.65, 1)} (15+ reps)"
        }
    }


def get_exercise_recommendations(
    muscle_group: Optional[str] = None,
    equipment: Optional[str] = None,
    injury_avoidance: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search and filter exercises based on muscle group, equipment, and injury contraindications.

    Args:
        muscle_group: Muscle group to filter by (e.g., 'Chest', 'Back', 'Quads', 'Shoulders', etc.).
        equipment: Available equipment filter (e.g., 'Dumbbell', 'Barbell', 'Bodyweight', 'Cable', 'Machine').
        injury_avoidance: Keywords describing injuries or limitations to avoid (e.g., 'knee', 'lower back', 'shoulder').

    Returns:
        List of matching exercise dictionaries with form cues and alternatives.
    """
    results = []
    injury_words = [w.strip().lower() for w in (injury_avoidance or "").split() if len(w.strip()) > 2]

    for ex in EXERCISE_DATABASE:
        # Muscle filter
        if muscle_group and muscle_group.lower() not in ex["muscle"].lower():
            continue

        # Equipment filter
        if equipment:
            eq_lower = equipment.lower()
            if "bodyweight" in eq_lower and ex["equipment"].lower() != "bodyweight":
                continue
            elif "dumbbell" in eq_lower and ex["equipment"].lower() not in ["dumbbell", "bodyweight"]:
                continue

        # Injury avoidance check
        is_contraindicated = False
        if injury_words:
            for contra in ex["contraindications"]:
                for word in injury_words:
                    if word in contra.lower():
                        is_contraindicated = True
                        break
                if is_contraindicated:
                    break

        if not is_contraindicated:
            results.append(ex)

    return results


def verify_exercise_safety(
    exercise_name: str,
    injuries_or_limitations: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verify if an exercise is safe given athlete injuries or movement limitations.

    Args:
        exercise_name: Name of the exercise to verify.
        injuries_or_limitations: Athlete injuries or constraints (e.g., 'lower back pain', 'knee tendonitis').

    Returns:
        Dictionary containing is_safe boolean, matched contraindications, risk level, and suggested alternative.
    """
    if not injuries_or_limitations or injuries_or_limitations.strip().lower() in ["none", "no", "n/a"]:
        return {
            "status": "success",
            "exercise_name": exercise_name,
            "is_safe": True,
            "risk_level": "LOW",
            "matched_contraindications": [],
            "alternative": None,
            "message": f"Exercise '{exercise_name}' is verified safe with no reported limitations."
        }

    injury_words = [w.strip().lower() for w in injuries_or_limitations.split() if len(w.strip()) > 2]
    matched_exercise = None
    for ex in EXERCISE_DATABASE:
        if ex["name"].lower() == exercise_name.lower() or exercise_name.lower() in ex["name"].lower():
            matched_exercise = ex
            break

    if not matched_exercise:
        # Unknown exercise - evaluate general keywords
        for ex in EXERCISE_DATABASE:
            for contra in ex["contraindications"]:
                for word in injury_words:
                    if word in contra.lower() and word in exercise_name.lower():
                        return {
                            "status": "success",
                            "exercise_name": exercise_name,
                            "is_safe": False,
                            "risk_level": "HIGH",
                            "matched_contraindications": [contra],
                            "alternative": ex.get("alternative", "Consult a physical therapist"),
                            "message": f"Exercise '{exercise_name}' may be contraindicated for '{injuries_or_limitations}'."
                        }
        return {
            "status": "success",
            "exercise_name": exercise_name,
            "is_safe": True,
            "risk_level": "LOW",
            "matched_contraindications": [],
            "alternative": None,
            "message": f"No contraindication conflicts found for '{exercise_name}'."
        }

    matched_contra = []
    for contra in matched_exercise["contraindications"]:
        for word in injury_words:
            if word in contra.lower():
                matched_contra.append(contra)

    is_safe = len(matched_contra) == 0
    return {
        "status": "success",
        "exercise_name": matched_exercise["name"],
        "is_safe": is_safe,
        "risk_level": "HIGH" if not is_safe else "LOW",
        "matched_contraindications": matched_contra,
        "alternative": matched_exercise.get("alternative") if not is_safe else None,
        "message": f"Exercise '{matched_exercise['name']}' is {'CONTRAINDICATED' if not is_safe else 'SAFE'}."
    }


def calculate_heart_rate_zones(age: int, resting_hr: Optional[int] = None) -> Dict[str, Any]:
    """
    Calculate target cardiovascular training heart rate zones using the Karvonen formula or Tanaka formula.

    Args:
        age: Age in years (14 to 100).
        resting_hr: Optional resting heart rate in bpm (40 to 120).

    Returns:
        Dictionary with max HR and training zones (Zone 1 to Zone 5).
    """
    if not (14 <= age <= 100):
        raise ValueError(f"Age ({age}) must be between 14 and 100 years.")

    # Tanaka formula: Max HR = 208 - (0.7 * age)
    max_hr = round(208 - (0.7 * age))

    if resting_hr and 40 <= resting_hr <= 120:
        # Karvonen Formula (Heart Rate Reserve)
        hrr = max_hr - resting_hr
        z1 = f"{round(resting_hr + hrr * 0.50)} - {round(resting_hr + hrr * 0.60)} bpm (Active Recovery)"
        z2 = f"{round(resting_hr + hrr * 0.60)} - {round(resting_hr + hrr * 0.70)} bpm (Aerobic Endurance)"
        z3 = f"{round(resting_hr + hrr * 0.70)} - {round(resting_hr + hrr * 0.80)} bpm (Tempo / Glycolytic)"
        z4 = f"{round(resting_hr + hrr * 0.80)} - {round(resting_hr + hrr * 0.90)} bpm (Lactate Threshold)"
        z5 = f"{round(resting_hr + hrr * 0.90)} - {max_hr} bpm (VO2 Max / Anaerobic Peak)"
        method = "Karvonen HRR"
    else:
        z1 = f"{round(max_hr * 0.50)} - {round(max_hr * 0.60)} bpm (Active Recovery)"
        z2 = f"{round(max_hr * 0.60)} - {round(max_hr * 0.70)} bpm (Aerobic Endurance)"
        z3 = f"{round(max_hr * 0.70)} - {round(max_hr * 0.80)} bpm (Tempo / Glycolytic)"
        z4 = f"{round(max_hr * 0.80)} - {round(max_hr * 0.90)} bpm (Lactate Threshold)"
        z5 = f"{round(max_hr * 0.90)} - {max_hr} bpm (VO2 Max / Anaerobic Peak)"
        method = "Tanaka Percentage"

    return {
        "status": "success",
        "max_heart_rate": max_hr,
        "calculation_method": method,
        "zones": {
            "zone_1_recovery": z1,
            "zone_2_endurance": z2,
            "zone_3_tempo": z3,
            "zone_4_threshold": z4,
            "zone_5_vo2max": z5
        }
    }


# Tool Declarations with Explicit JSON Schemas for LLM Tool Calling
TOOL_DECLARATIONS = [
    {
        "name": "calculate_fitness_metrics",
        "description": "Calculate BMR (Mifflin-St Jeor), TDEE, caloric targets, and macronutrient partitioning (protein, carbs, fats, hydration) for an athlete.",
        "parameters": {
            "type": "object",
            "properties": {
                "weight_kg": {"type": "number", "description": "Athlete body weight in kg (30.0 - 300.0)"},
                "height_cm": {"type": "number", "description": "Athlete height in cm (100.0 - 250.0)"},
                "age": {"type": "integer", "description": "Athlete age in years (14 - 100)"},
                "gender": {"type": "string", "enum": ["Male", "Female", "Other / Non-binary"], "description": "Gender for metabolic calculation"},
                "activity_level": {"type": "string", "description": "Activity level descriptor (Sedentary, Lightly Active, Moderately Active, Very Active)"},
                "goal": {"type": "string", "description": "Target fitness goal (e.g., Hypertrophy, Strength, Fat Loss)"}
            },
            "required": ["weight_kg", "height_cm", "age"]
        }
    },
    {
        "name": "get_exercise_recommendations",
        "description": "Search and filter the curated exercise database by muscle group, available equipment, and injury contraindications.",
        "parameters": {
            "type": "object",
            "properties": {
                "muscle_group": {"type": "string", "description": "Muscle group (Chest, Back, Shoulders, Quads, Hamstrings, Glutes, Biceps, Triceps, Core)"},
                "equipment": {"type": "string", "description": "Equipment filter (Barbell, Dumbbell, Bodyweight, Cable, Machine)"},
                "injury_avoidance": {"type": "string", "description": "Injuries or joint pain to avoid (e.g., 'knee pain', 'lower back pain', 'shoulder impingement')"}
            }
        }
    },
    {
        "name": "verify_exercise_safety",
        "description": "Audit an individual exercise against athlete injuries or joint limitations to check for contraindications.",
        "parameters": {
            "type": "object",
            "properties": {
                "exercise_name": {"type": "string", "description": "Name of the exercise to audit"},
                "injuries_or_limitations": {"type": "string", "description": "Athlete injuries or limitations"}
            },
            "required": ["exercise_name"]
        }
    },
    {
        "name": "calculate_one_rep_max",
        "description": "Calculate estimated 1RM and percentage load zones (strength, hypertrophy, endurance) from a completed weight and rep performance.",
        "parameters": {
            "type": "object",
            "properties": {
                "weight": {"type": "number", "description": "Weight lifted in kg or lbs"},
                "reps": {"type": "integer", "description": "Reps performed (1-12)"}
            },
            "required": ["weight", "reps"]
        }
    },
    {
        "name": "calculate_heart_rate_zones",
        "description": "Calculate cardiovascular training heart rate zones (Zone 1 to Zone 5) based on age and optional resting heart rate.",
        "parameters": {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "description": "Athlete age in years"},
                "resting_hr": {"type": "integer", "description": "Optional resting heart rate in bpm"}
            },
            "required": ["age"]
        }
    }
]

TOOL_FUNCTION_MAP = {
    "calculate_fitness_metrics": calculate_fitness_metrics,
    "get_exercise_recommendations": get_exercise_recommendations,
    "verify_exercise_safety": verify_exercise_safety,
    "calculate_one_rep_max": calculate_one_rep_max,
    "calculate_heart_rate_zones": calculate_heart_rate_zones
}


def execute_tool_with_recovery(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool with guided error handling and structured recovery hints for the LLM.

    Args:
        tool_name: Name of tool to execute.
        arguments: Arguments dictionary.

    Returns:
        Execution result dictionary or guided error recovery dictionary.
    """
    if tool_name not in TOOL_FUNCTION_MAP:
        return {
            "status": "error",
            "error_type": "TOOL_NOT_FOUND",
            "message": f"Tool '{tool_name}' does not exist.",
            "available_tools": list(TOOL_FUNCTION_MAP.keys()),
            "retry_guidance": "Please select a valid tool name from the available_tools list."
        }

    func = TOOL_FUNCTION_MAP[tool_name]
    try:
        result = func(**arguments)
        if isinstance(result, list):
            return {"status": "success", "results": result, "count": len(result)}
        return result
    except TypeError as te:
        return {
            "status": "error",
            "error_type": "INVALID_ARGUMENTS",
            "tool_name": tool_name,
            "message": f"Invalid arguments passed to {tool_name}: {te}",
            "provided_arguments": arguments,
            "retry_guidance": "Check tool schema and supply the required parameters with correct types."
        }
    except ValueError as ve:
        return {
            "status": "error",
            "error_type": "VALUE_OUT_OF_BOUNDS",
            "tool_name": tool_name,
            "message": str(ve),
            "provided_arguments": arguments,
            "retry_guidance": "Adjust argument values to fit within acceptable physiological ranges."
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "EXECUTION_FAILURE",
            "tool_name": tool_name,
            "message": f"Unexpected execution error: {e}",
            "retry_guidance": "Review parameters and retry with valid inputs."
        }

