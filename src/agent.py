"""Workout Planning Agent wrapper providing backwards compatibility and multi-agent coordination."""

import os
from typing import Dict, Any, List, Optional

from src.models import UserProfile, WorkoutPlan
from src.orchestrator import CoordinatorAgent
from src.observability import ExecutionTracer, logger


class WorkoutAgent:
    """
    Backwards-compatible WorkoutAgent interface delegating to CoordinatorAgent
    with multi-agent orchestration, dynamic model routing, guardrails, and persistent memory.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        vertexai: bool = False,
        project: Optional[str] = None,
        location: Optional[str] = "us-central1",
        model_name: str = "gemini-2.5-flash",
        deep_model: str = "gemini-2.5-pro",
        demo_mode: bool = False,
        db_path: str = "fitforge_memory.db"
    ):
        self.model_name = model_name
        self.demo_mode = demo_mode
        self.coordinator = CoordinatorAgent(
            api_key=api_key,
            vertexai=vertexai,
            project=project,
            location=location,
            default_model=model_name,
            deep_model=deep_model,
            demo_mode=demo_mode,
            db_path=db_path
        )
        self.tracer = ExecutionTracer()
        self.chat_history: List[Dict[str, str]] = []
        self.current_plan: Optional[Dict[str, Any]] = None

    def generate_plan(self, profile: UserProfile, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a complete workout plan using the multi-agent pipeline.
        """
        result = self.coordinator.generate_plan(profile=profile, session_id=session_id)
        self.current_plan = result
        self.tracer = self.coordinator.nutrition_agent.client or self.tracer
        self.chat_history = [
            {"role": "user", "content": f"Generate workout plan for: {profile.goal.value}"},
            {"role": "assistant", "content": result["plan_markdown"]}
        ]
        return result

    def chat(self, user_message: str, session_id: str = "default_session") -> str:
        """
        Coaching chat interaction with input guardrails and specialist agent routing.
        """
        self.chat_history.append({"role": "user", "content": user_message})
        result = self.coordinator.chat(user_message=user_message, session_id=session_id)
        reply = result.get("reply", "No response.")
        self.chat_history.append({"role": "assistant", "content": reply})
        return reply
