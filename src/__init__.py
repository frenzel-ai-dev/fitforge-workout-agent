"""FitForge Workout Planning Agent package."""

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
from src.tools import (
    calculate_fitness_metrics,
    get_exercise_recommendations,
    verify_exercise_safety,
    calculate_one_rep_max,
    calculate_heart_rate_zones,
    execute_tool_with_recovery,
    TOOL_DECLARATIONS
)
from src.agent import WorkoutAgent
from src.orchestrator import CoordinatorAgent
from src.guardrails import InputGuardrail, OutputGuardrail
from src.hitl import HITLManager
from src.memory import MemoryManager, SQLiteMemoryStore, HistoryCompactor
from src.observability import ExecutionTracer, JSONLogFormatter, logger
from src.pii import PIIRedactor
from src.secrets import SecretManager

__version__ = "1.0.0"
