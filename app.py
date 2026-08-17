"""Streamlit UI for FitForge AI - Multi-Agent Workout Planning & Coaching Agent."""

import os
import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.models import (
    UserProfile,
    FitnessGoal,
    ExperienceLevel,
    EquipmentAvailability,
    Gender,
    WorkoutPlan
)
from src.orchestrator import CoordinatorAgent
from src.memory import SQLiteMemoryStore
from src.secrets import SecretManager

# Page configuration
st.set_page_config(
    page_title="FitForge AI | Multi-Agent Workout Planning",
    page_icon="🏋️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #555555;
        margin-bottom: 1.5rem;
    }
    .hitl-alert {
        background-color: #FFF3E0;
        border-left: 5px solid #FF9800;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .agent-badge {
        display: inline-block;
        background-color: #E3F2FD;
        color: #1565C0;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "workout_plan_result" not in st.session_state:
        st.session_state.workout_plan_result = None
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = "default_session"
    if "memory_store" not in st.session_state:
        st.session_state.memory_store = SQLiteMemoryStore()
    if "hitl_approved" not in st.session_state:
        st.session_state.hitl_approved = False


init_session_state()

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/barbell.png", width=64)
    st.title("FitForge Multi-Agent")

    # Authentication & Model Selection
    with st.expander("🔑 AI & Secret Manager", expanded=False):
        auth_mode = st.radio(
            "Authentication Mode",
            ["Google AI Studio (API Key)", "Vertex AI & Secret Manager", "Demo / Mock Mode"],
            index=0
        )

        api_key = None
        project = None
        location = "us-central1"
        demo_mode = False

        if auth_mode == "Google AI Studio (API Key)":
            env_key = SecretManager.get_gemini_api_key(default="")
            api_key = st.text_input("Gemini API Key", value=env_key or "", type="password")
            if not api_key:
                st.info("Tip: Get a free key at [Google AI Studio](https://aistudio.google.com/app/api-keys)")
        elif auth_mode == "Vertex AI & Secret Manager":
            env_proj = os.getenv("GOOGLE_CLOUD_PROJECT", "")
            project = st.text_input("Google Cloud Project ID", value=env_proj)
            location = st.text_input("Location", value=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
        else:
            demo_mode = True
            st.success("Demo mode active (deterministic offline generator)")

        st.caption("Dynamic Model Routing:")
        st.markdown("- **Router & Fast Tools:** `gemini-2.5-flash`\n- **Deep Periodization:** `gemini-2.5-pro`")

    # Persistent Session History
    with st.expander("💾 Saved Sessions", expanded=False):
        sessions = st.session_state.memory_store.list_sessions()
        if sessions:
            selected_sess = st.selectbox(
                "Load Past Session",
                options=[s["session_id"] for s in sessions],
                format_func=lambda sid: f"{sid} ({next((s['title'] for s in sessions if s['session_id'] == sid), '')})"
            )
            if st.button("📂 Load Selected Session"):
                loaded = st.session_state.memory_store.load_session(selected_sess)
                if loaded and loaded.get("workout_plan"):
                    st.session_state.workout_plan_result = {
                        "session_id": loaded["session_id"],
                        "plan_markdown": loaded.get("chat_history", [{}])[-1].get("content", ""),
                        "plan_structured": loaded.get("workout_plan"),
                        "metrics": loaded.get("workout_plan", {}).get("nutrition", {}),
                        "profile": loaded.get("profile", {}),
                        "safety_audit": loaded.get("workout_plan", {}).get("safety_audit", {}),
                        "hitl_request": loaded.get("workout_plan", {}).get("hitl_request", {}),
                        "trace_summary": {"total_events": 0, "total_duration_ms": 0, "events": [], "spans": []}
                    }
                    st.session_state.chat_messages = loaded.get("chat_history", [])
                    st.session_state.session_id = selected_sess
                    st.success(f"Loaded session '{selected_sess}'!")
                    st.rerun()
        else:
            st.caption("No saved sessions in SQLite yet.")

    st.subheader("👤 Athlete Profile")

    goal = st.selectbox("Primary Fitness Goal", [g.value for g in FitnessGoal], index=0)
    experience = st.selectbox("Experience Level", [e.value for e in ExperienceLevel], index=1)
    days_per_week = st.slider("Workout Days Per Week", min_value=2, max_value=6, value=4)
    equipment = st.selectbox("Available Equipment", [eq.value for eq in EquipmentAvailability], index=0)

    with st.expander("📊 Biometrics & Metabolism", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            age = st.number_input("Age", min_value=15, max_value=90, value=28)
            gender_val = st.selectbox("Gender", [g.value for g in Gender], index=0)
        with col_b:
            weight_kg = st.number_input("Weight (kg)", min_value=35.0, max_value=200.0, value=78.0, step=0.5)
            height_cm = st.number_input("Height (cm)", min_value=120.0, max_value=230.0, value=178.0, step=1.0)

        activity_level = st.selectbox(
            "Daily Activity Level",
            [
                "Sedentary (desk job, little exercise)",
                "Lightly Active (exercise 1-3 days/wk)",
                "Moderately Active (exercise 3-5 days/wk)",
                "Very Active (hard exercise 6-7 days/wk)"
            ],
            index=2
        )

    injuries = st.text_input(
        "Injuries or Limitations to Avoid",
        value="None",
        placeholder="e.g. Mild lower back pain, bad left knee"
    )

    preferred_split = st.selectbox(
        "Split Preference",
        ["Auto (Recommended by Coach)", "Push / Pull / Legs", "Upper / Lower", "Full Body", "Bro Split (1 muscle/day)"],
        index=0
    )

    generate_clicked = st.button("⚡ Generate Multi-Agent Plan", type="primary", use_container_width=True)

# ----------------- MAIN VIEW -----------------
st.markdown('<div class="main-header">🏋️‍♂️ FitForge AI - Multi-Agent Workout Planning System</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">'
    '<span class="agent-badge">🧭 Coordinator Agent</span>'
    '<span class="agent-badge">🥗 Nutrition Specialist</span>'
    '<span class="agent-badge">🛠️ Exercise Specialist</span>'
    '<span class="agent-badge">📈 Periodization Specialist</span>'
    '<span class="agent-badge">🛡️ Safety Guardrail</span>'
    '</div>',
    unsafe_allow_html=True
)

# Handle Plan Generation
if generate_clicked:
    profile = UserProfile(
        age=age,
        gender=Gender(gender_val),
        weight_kg=weight_kg,
        height_cm=height_cm,
        activity_level=activity_level,
        goal=FitnessGoal(goal),
        experience_level=ExperienceLevel(experience),
        days_per_week=days_per_week,
        equipment=EquipmentAvailability(equipment),
        injuries_or_limitations=injuries if injuries.strip() else "None",
        preferred_split=preferred_split
    )

    with st.spinner("🤖 FitForge Multi-Agent Pipeline is executing (Nutrition ➔ Exercise ➔ Periodization ➔ Safety Guardrail)..."):
        coordinator = CoordinatorAgent(
            api_key=api_key if auth_mode == "Google AI Studio (API Key)" else None,
            vertexai=(auth_mode == "Vertex AI & Secret Manager"),
            project=project if auth_mode == "Vertex AI & Secret Manager" else None,
            location=location,
            demo_mode=demo_mode
        )
        st.session_state.agent = coordinator
        st.session_state.session_id = f"sess_{int(os.times().system * 1000)}"

        result = coordinator.generate_plan(profile, session_id=st.session_state.session_id)
        st.session_state.workout_plan_result = result
        st.session_state.chat_messages = [
            {"role": "user", "content": f"Create workout plan for {profile.goal.value}"},
            {"role": "assistant", "content": result.get("plan_markdown", "")}
        ]
        st.session_state.hitl_approved = False

# Display Result if available
if st.session_state.workout_plan_result:
    result = st.session_state.workout_plan_result
    metrics = result.get("metrics", {})
    hitl = result.get("hitl_request", {})

    # Human-in-the-Loop (HITL) Alert Card
    if hitl.get("requires_approval") and not st.session_state.hitl_approved:
        st.markdown(f"""
        <div class="hitl-alert">
            <h4 style="color: #E65100; margin-top: 0;">⚠️ Human-in-the-Loop (HITL) Approval Required</h4>
            <p><strong>Action Type:</strong> <code>{hitl.get('action_type')}</code> | <strong>Risk Level:</strong> <code>{hitl.get('risk_level')}</code></p>
            <p>{hitl.get('description')}</p>
            <p><strong>Potential Risks:</strong></p>
            <ul>{''.join(f'<li>{r}</li>' for r in hitl.get('potential_risks', []))}</ul>
            <p><strong>Recommended Alternative:</strong> {hitl.get('recommended_alternative')}</p>
        </div>
        """, unsafe_allow_html=True)

        col_hitl1, col_hitl2 = st.columns(2)
        with col_hitl1:
            if st.button("✅ I Understand and Approve Proposed Plan", type="primary", use_container_width=True):
                st.session_state.hitl_approved = True
                st.success("Action confirmed by athlete.")
                st.rerun()
        with col_hitl2:
            if st.button("🛡️ Use Safer Recommended Alternative", use_container_width=True):
                st.session_state.hitl_approved = True
                st.info(f"Alternative Applied: {hitl.get('recommended_alternative')}")

    # Top Metrics Cards
    st.subheader("🎯 Target Nutritional & Metabolic Baseline")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Daily Calories", f"{metrics.get('target_calories', 0)} kcal", delta=f"TDEE {metrics.get('tdee_calories', 0)}")
    with col2:
        st.metric("Protein Target", f"{metrics.get('protein_g', 0)} g", delta="2.0 g/kg")
    with col3:
        st.metric("Carbohydrates", f"{metrics.get('carbs_g', 0)} g")
    with col4:
        st.metric("Fats", f"{metrics.get('fats_g', 0)} g")
    with col5:
        st.metric("Hydration", f"{metrics.get('hydration_liters', 0)} L/day")

    st.divider()

    # Plan Tabs
    tab_plan, tab_export, tab_traces, tab_safety = st.tabs([
        "📋 Workout Routine",
        "💾 Export & JSON Schemas",
        "🔍 Multi-Agent OTEL Traces",
        "🛡️ Safety Guardrail Report"
    ])

    with tab_plan:
        st.markdown(result.get("plan_markdown", ""))

    with tab_export:
        st.subheader("Export Workout Plan")
        plan_text = result.get("plan_markdown", "")
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            st.download_button(
                label="📥 Download Plan as Markdown (.md)",
                data=plan_text,
                file_name="fitforge_workout_plan.md",
                mime="text/markdown",
                use_container_width=True
            )
        with col_exp2:
            structured_plan = result.get("plan_structured", {})
            st.download_button(
                label="📥 Download Structured JSON (Pydantic Schema)",
                data=json.dumps(structured_plan, indent=2),
                file_name="fitforge_workout_plan.json",
                mime="application/json",
                use_container_width=True
            )

        with st.expander("🔍 View Raw JSON Schema Payload", expanded=False):
            st.json(result.get("plan_structured", {}))

    with tab_traces:
        st.subheader("OpenTelemetry Traces & Intent Logs")
        traces = result.get("trace_summary", {})
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            st.metric("Total Pipeline Latency", f"{traces.get('total_duration_ms', 0)} ms")
        with col_t2:
            st.metric("Trace ID", str(traces.get("trace_id", "N/A"))[:12] + "...")
        with col_t3:
            st.metric("Total Events / Spans", f"{traces.get('total_events', 0)} / {traces.get('total_spans', 0)}")

        st.markdown("#### Recorded Execution Spans")
        if traces.get("spans"):
            st.dataframe(traces.get("spans"), use_container_width=True)

        st.markdown("#### Chronological Event Log (with Pre-Execution Intent & PII Redaction)")
        st.json(traces.get("events", []))

    with tab_safety:
        st.subheader("Automated Biomechanical & Safety Audit")
        safety = result.get("safety_audit", {})
        status_color = "green" if safety.get("is_safe", True) else "red"
        st.markdown(f"**Safety Status:** :{status_color}[{'PASSED' if safety.get('is_safe', True) else 'MODIFIED'}]")
        st.write(f"**Risk Level:** `{safety.get('risk_level', 'LOW')}`")
        st.write(f"**Contraindications Checked:** {', '.join(safety.get('contraindications_checked', [])) or 'None'}")
        if safety.get("flagged_exercises"):
            st.warning("**Flagged Exercises:**")
            for f in safety.get("flagged_exercises", []):
                st.write(f"- {f}")
        if safety.get("modifications_applied"):
            st.info("**Modifications Applied by Guardrail:**")
            for m in safety.get("modifications_applied", []):
                st.write(f"- {m}")

    st.divider()

    # Interactive Chat with Coach Agent
    st.subheader("💬 Interactive Multi-Turn Coaching")
    st.caption("Ask questions, request exercise swaps (e.g. 'Swap squats for leg press'), or tweak caloric targets.")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask Coach FitForge a question or request a change..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Specialist Agents Reasoning..."):
                if st.session_state.agent:
                    chat_res = st.session_state.agent.chat(prompt, session_id=st.session_state.session_id)
                    reply = chat_res.get("reply", "Response unavailable.")
                else:
                    coordinator = CoordinatorAgent(demo_mode=demo_mode)
                    st.session_state.agent = coordinator
                    chat_res = coordinator.chat(prompt, session_id=st.session_state.session_id)
                    reply = chat_res.get("reply", "Response unavailable.")

                st.markdown(reply)
                st.session_state.chat_messages.append({"role": "assistant", "content": reply})

else:
    st.info("👈 Set your fitness goals, equipment, and injuries in the sidebar and click **'Generate Multi-Agent Plan'** to start!")

    col_feat1, col_feat2, col_feat3 = st.columns(3)
    with col_feat1:
        st.markdown("### 🧭 Multi-Agent Pipeline")
        st.markdown("- Dedicated Nutrition, Exercise, & Periodization sub-agents\n- Dynamic routing to Gemini 2.5 Flash & Pro\n- Deterministic tool schemas & guided error recovery")
    with col_feat2:
        st.markdown("### 🛡️ Safety & HITL Guardrails")
        st.markdown("- Automated biomechanical contraindication scanner\n- Human-in-the-Loop approval for high-stakes deficits\n- Input sanitization & prompt injection defense")
    with col_feat3:
        st.markdown("### 🔍 Observability & Persistence")
        st.markdown("- OpenTelemetry-compatible tracing & spans\n- Pre-execution intent logs & PII redaction\n- SQLite persistent memory with history compaction")
