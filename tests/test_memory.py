"""Unit tests for SQLite persistent memory store, async memory ops, and history compaction."""

import os
import pytest
import asyncio
from src.models import UserProfile, FitnessGoal, Gender
from src.memory import SQLiteMemoryStore, HistoryCompactor, MemoryManager


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_fitforge_memory.db")


def test_sqlite_memory_store_crud(temp_db_path):
    """Test saving and loading sessions and athlete facts."""
    store = SQLiteMemoryStore(db_path=temp_db_path)
    profile = UserProfile(
        age=28,
        gender=Gender.MALE,
        weight_kg=78.0,
        goal=FitnessGoal.HYPERTROPHY
    )

    # Save session
    store.save_session(
        session_id="sess_123",
        user_id="user_123",
        profile=profile,
        chat_messages=[
            {"role": "user", "content": "I have slight left knee pain."},
            {"role": "assistant", "content": "Noted, I will adjust quad exercises."}
        ],
        workout_plan={"plan_title": "Test Plan"},
        title="Test Session 1"
    )

    # Load session
    loaded = store.load_session("sess_123")
    assert loaded is not None
    assert loaded["session_id"] == "sess_123"
    assert loaded["user_id"] == "user_123"
    assert loaded["profile"]["age"] == 28
    assert len(loaded["chat_history"]) == 2
    assert loaded["workout_plan"]["plan_title"] == "Test Plan"

    # Save and get athlete facts
    store.save_athlete_fact("user_123", "injury", "knee_pain", "Left knee discomfort reported")
    facts = store.get_athlete_facts("user_123")
    assert len(facts) == 1
    assert facts[0]["key"] == "knee_pain"


def test_history_compactor():
    """Test history compaction when chat turns exceed threshold."""
    compactor = HistoryCompactor(max_turns=4, recent_turns_to_keep=2)

    turns = [
        {"role": "user", "content": "Hi, I have lower back pain."},
        {"role": "assistant", "content": "I will avoid heavy spinal loading."},
        {"role": "user", "content": "Can we swap deadlifts for glute bridges?"},
        {"role": "assistant", "content": "Yes, swapped Romanian Deadlifts with Glute Bridges."},
        {"role": "user", "content": "What is my protein target?"},
        {"role": "assistant", "content": "Your protein target is 160g daily."}
    ]

    assert compactor.should_compact(turns) is True

    compacted, summary, extracted_facts = compactor.compact_history(turns)
    assert len(compacted) < len(turns)
    assert compacted[0]["role"] == "system"
    assert "CONVERSATION SUMMARY" in compacted[0]["content"]
    assert len(extracted_facts) >= 1


def test_async_memory_manager(temp_db_path):
    """Test async memory manager turn persistence and compaction."""
    async def _test():
        manager = MemoryManager(db_path=temp_db_path)

        chat_history = await manager.process_and_persist_turn_async(
            session_id="sess_async",
            user_id="athlete_01",
            user_message="I have bad shoulder impingement so please avoid overhead press",
            assistant_response="Understood, replacing overhead press with dumbbell lateral raises.",
            model="gemini-2.5-flash"
        )

        assert len(chat_history) == 2
        facts = await manager.store.get_athlete_facts_async("athlete_01")
        assert len(facts) >= 1
        assert "shoulder" in facts[0]["value"].lower()

    asyncio.run(_test())

