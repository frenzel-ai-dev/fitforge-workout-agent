"""Persistent SQLite session storage, async memory operations, and history compaction for FitForge AI."""

import os
import json
import time
import sqlite3
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import asdict

from src.models import UserProfile, WorkoutPlan, MemoryFact, ConversationTurn
from src.pii import PIIRedactor
from src.observability import logger


class SQLiteMemoryStore:
    """Persistent SQLite store for sessions, user profiles, conversation histories, and athlete facts."""

    def __init__(self, db_path: str = "fitforge_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    model TEXT,
                    tool_calls_json TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS athlete_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    fact_type TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workout_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            conn.commit()

    # ---------------- Synchronous Methods ----------------

    def save_session(
        self,
        session_id: str,
        user_id: str,
        profile: Optional[UserProfile] = None,
        chat_messages: Optional[List[Dict[str, Any]]] = None,
        workout_plan: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ) -> None:
        """Save or update a session with profile, messages, and plan."""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (session_id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    title = COALESCE(excluded.title, sessions.title)
            """, (session_id, user_id, title or "Workout Session", now, now))

            if profile:
                profile_json = profile.model_dump_json()
                cursor.execute("""
                    INSERT INTO user_profiles (user_id, profile_json, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        profile_json = excluded.profile_json,
                        updated_at = excluded.updated_at
                """, (user_id, profile_json, now))

            if workout_plan:
                plan_json = json.dumps(PIIRedactor.redact_data(workout_plan))
                cursor.execute("""
                    INSERT INTO workout_plans (session_id, plan_json, created_at)
                    VALUES (?, ?, ?)
                """, (session_id, plan_json, now))

            if chat_messages:
                # Save only new messages
                cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
                for msg in chat_messages:
                    safe_content = PIIRedactor.redact_text(msg.get("content", ""))
                    tool_calls_json = json.dumps(msg.get("tool_calls")) if msg.get("tool_calls") else None
                    cursor.execute("""
                        INSERT INTO chat_history (session_id, role, content, timestamp, model, tool_calls_json)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        msg.get("role", "user"),
                        safe_content,
                        msg.get("timestamp", now),
                        msg.get("model"),
                        tool_calls_json
                    ))

            conn.commit()

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session details including profile, chat history, and latest workout plan."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            session_row = cursor.fetchone()
            if not session_row:
                return None

            user_id = session_row["user_id"]

            # Load profile
            cursor.execute("SELECT profile_json FROM user_profiles WHERE user_id = ?", (user_id,))
            profile_row = cursor.fetchone()
            profile = json.loads(profile_row["profile_json"]) if profile_row else None

            # Load chat history
            cursor.execute("SELECT role, content, timestamp, model, tool_calls_json FROM chat_history WHERE session_id = ? ORDER BY id ASC", (session_id,))
            chat_rows = cursor.fetchall()
            chat_history = [
                {
                    "role": r["role"],
                    "content": r["content"],
                    "timestamp": r["timestamp"],
                    "model": r["model"],
                    "tool_calls": json.loads(r["tool_calls_json"]) if r["tool_calls_json"] else None
                }
                for r in chat_rows
            ]

            # Load latest plan
            cursor.execute("SELECT plan_json FROM workout_plans WHERE session_id = ? ORDER BY id DESC LIMIT 1", (session_id,))
            plan_row = cursor.fetchone()
            workout_plan = json.loads(plan_row["plan_json"]) if plan_row else None

            return {
                "session_id": session_id,
                "user_id": user_id,
                "title": session_row["title"],
                "created_at": session_row["created_at"],
                "updated_at": session_row["updated_at"],
                "profile": profile,
                "chat_history": chat_history,
                "workout_plan": workout_plan
            }

    def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all saved sessions."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("SELECT * FROM sessions WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
            else:
                cursor.execute("SELECT * FROM sessions ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def save_athlete_fact(self, user_id: str, fact_type: str, key: str, value: str) -> None:
        """Persist a discovered athlete fact (e.g. injury preference, favorite lift)."""
        safe_value = PIIRedactor.redact_text(value)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO athlete_facts (user_id, fact_type, key, value, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, fact_type, key, safe_value, time.time()))
            conn.commit()

    def get_athlete_facts(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve all recorded facts for an athlete."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT fact_type, key, value, timestamp FROM athlete_facts WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    # ---------------- Asynchronous Methods ----------------

    async def save_session_async(
        self,
        session_id: str,
        user_id: str,
        profile: Optional[UserProfile] = None,
        chat_messages: Optional[List[Dict[str, Any]]] = None,
        workout_plan: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ) -> None:
        """Async wrapper for save_session."""
        await asyncio.to_thread(
            self.save_session,
            session_id=session_id,
            user_id=user_id,
            profile=profile,
            chat_messages=chat_messages,
            workout_plan=workout_plan,
            title=title
        )

    async def load_session_async(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Async wrapper for load_session."""
        return await asyncio.to_thread(self.load_session, session_id)

    async def get_athlete_facts_async(self, user_id: str) -> List[Dict[str, Any]]:
        """Async wrapper for get_athlete_facts."""
        return await asyncio.to_thread(self.get_athlete_facts, user_id)

    async def save_athlete_fact_async(self, user_id: str, fact_type: str, key: str, value: str) -> None:
        """Async wrapper for save_athlete_fact."""
        await asyncio.to_thread(self.save_athlete_fact, user_id, fact_type, key, value)


class HistoryCompactor:
    """
    Context & Memory Compaction engine.
    Extracts durable athlete facts and summarizes older conversation turns
    to prevent context window bloat while preserving recent verbatim turns.
    """

    def __init__(self, max_turns: int = 6, recent_turns_to_keep: int = 4):
        self.max_turns = max_turns
        self.recent_turns_to_keep = recent_turns_to_keep

    def should_compact(self, chat_history: List[Dict[str, Any]]) -> bool:
        """Check if chat history exceeds compaction threshold."""
        return len(chat_history) > self.max_turns

    def extract_facts_from_turn(self, user_message: str) -> List[Tuple[str, str, str]]:
        """
        Heuristic extraction of athlete constraints and preferences from chat turns.
        Returns list of (fact_type, key, value).
        """
        facts = []
        msg_lower = user_message.lower()

        # Injury / Pain facts
        for joint in ["knee", "shoulder", "lower back", "wrist", "elbow", "hip", "ankle", "neck"]:
            if joint in msg_lower and any(w in msg_lower for w in ["pain", "hurt", "tweak", "strain", "injury", "surgery", "avoid"]):
                facts.append(("injury", f"{joint}_limitation", f"Athlete reported {joint} discomfort or limitation in: '{user_message[:100]}'"))

        # Exercise Swap facts
        if "swap" in msg_lower or "substitute" in msg_lower or "replace" in msg_lower:
            facts.append(("preference", "exercise_substitution", f"Exercise adjustment requested: '{user_message[:100]}'"))

        # Nutrition / Calorie adjustments
        if any(w in msg_lower for w in ["calorie", "protein", "carbs", "fats", "diet", "meal"]):
            facts.append(("nutrition_preference", "dietary_tweak", f"Dietary guidance discussed: '{user_message[:100]}'"))

        return facts

    def compact_history(
        self,
        chat_history: List[Dict[str, Any]],
        existing_summary: str = ""
    ) -> Tuple[List[Dict[str, Any]], str, List[Tuple[str, str, str]]]:
        """
        Compacts older turns into a consolidated context summary block.

        Returns:
            (compacted_chat_history, updated_summary, extracted_facts)
        """
        if not self.should_compact(chat_history):
            return chat_history, existing_summary, []

        turns_to_compact = chat_history[:-self.recent_turns_to_keep]
        recent_turns = chat_history[-self.recent_turns_to_keep:]

        all_extracted_facts: List[Tuple[str, str, str]] = []
        summary_lines = []
        if existing_summary:
            summary_lines.append(existing_summary)

        for turn in turns_to_compact:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role == "user":
                extracted = self.extract_facts_from_turn(content)
                all_extracted_facts.extend(extracted)
                summary_lines.append(f"- Athlete: {content[:120]}")
            elif role == "assistant":
                summary_lines.append(f"- Coach: {content[:120]}...")

        updated_summary = "\n".join(summary_lines[-8:])  # Keep top 8 salient bullet points
        compacted_history = [
            {"role": "system", "content": f"[CONVERSATION SUMMARY & ATHLETE PREFERENCES]\n{updated_summary}"}
        ] + recent_turns

        return compacted_history, updated_summary, all_extracted_facts

    async def compact_history_async(
        self,
        chat_history: List[Dict[str, Any]],
        existing_summary: str = ""
    ) -> Tuple[List[Dict[str, Any]], str, List[Tuple[str, str, str]]]:
        """Async wrapper for history compaction."""
        return await asyncio.to_thread(self.compact_history, chat_history, existing_summary)


class MemoryManager:
    """Unified manager coordinating SQLite session persistence and history compaction."""

    def __init__(self, db_path: str = "fitforge_memory.db"):
        self.store = SQLiteMemoryStore(db_path=db_path)
        self.compactor = HistoryCompactor()

    async def process_and_persist_turn_async(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        assistant_response: str,
        model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Add user turn, extract facts, apply compaction if needed, and save to SQLite."""
        session = await self.store.load_session_async(session_id)
        chat_history = session.get("chat_history", []) if session else []

        now = time.time()
        chat_history.append({"role": "user", "content": user_message, "timestamp": now})
        chat_history.append({"role": "assistant", "content": assistant_response, "timestamp": now + 0.1, "model": model})

        # Extract and save any facts
        facts = self.compactor.extract_facts_from_turn(user_message)
        for fact_type, key, value in facts:
            await self.store.save_athlete_fact_async(user_id, fact_type, key, value)

        # Compact if needed
        if self.compactor.should_compact(chat_history):
            chat_history, summary, _ = await self.compactor.compact_history_async(chat_history)

        await self.store.save_session_async(
            session_id=session_id,
            user_id=user_id,
            chat_messages=chat_history
        )

        return chat_history
