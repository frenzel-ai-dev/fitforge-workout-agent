"""Streamlit UI for FitForge AI - Workout Planning Agent."""

import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables if .env exists
load_dotenv()

from src.models import (
    UserProfile,
    FitnessGoal,
    ExperienceLevel,
    EquipmentAvailability,
    Gender
)
from src.agent import WorkoutAgent

# Page configuration
st.set_page_config(
    page_title="FitForge AI | Workout Planning Agent",
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
        font-size: 1.1rem;
        color: #616161;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 4px solid #1E88E5;
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


init_session_state()

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/barbell.png", width=64)
    st.title("FitForge Setup")

    # Authentication section
    with st.expander("🔑 AI & Authentication Settings", expanded=False):
        auth_mode = st.radio(
            "Authentication Method",
            ["Google AI Studio (API Key)", "Vertex AI (ADC)", "Demo / Mock Mode"],
            index=0
        )

        api_key = None
        project = None
        location = "us-central1"
        demo_mode = False

        if auth_mode == "Google AI Studio (API Key)":
            env_key = os.getenv("GEMINI_API_KEY", "")
            api_key = st.text_input("Gemini API Key", value=env_key, type="password")
            if not api_key:
                st.info("Tip: Get a free key at [Google AI Studio](https://aistudio.google.com/app/api-keys)")
        elif auth_mode == "Vertex AI (ADC)":
            env_proj = os.getenv("GOOGLE_CLOUD_PROJECT", "")
            project = st.text_input("Google Cloud Project ID", value=env_proj)
            location = st.text_input("Location", value=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
        else:
            demo_mode = True
            st.success("Demo mode active (rule-based offline generator)")

        model_name = st.selectbox(
            "Model",
            ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
            index=0
        )

    st.subheader("👤 Athlete Profile")

    goal = st.selectbox(
        "Primary Fitness Goal",
        [g.value for g in FitnessGoal],
        index=0
    )

    experience = st.selectbox(
        "Experience Level",
        [e.value for e in ExperienceLevel],
        index=1
    )

    days_per_week = st.slider("Workout Days Per Week", min_value=2, max_value=6, value=4)

    equipment = st.selectbox(
        "Available Equipment",
        [eq.value for eq in EquipmentAvailability],
        index=0
    )

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

    generate_clicked = st.button("⚡ Generate Workout Plan", type="primary", use_container_width=True)

# ----------------- MAIN VIEW -----------------
st.markdown('<div class="main-header">🏋️‍♂️ FitForge AI - Autonomous Workout Planning Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Personalized training routines, injury-aware exercise selection, progressive overload schedules, and science-backed nutrition.</div>', unsafe_allow_html=True)

# Handle Plan Generation
if generate_clicked:
    # Instantiate UserProfile
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

    with st.spinner("🤖 FitForge Agent is analyzing your profile, running fitness calculations, and generating your plan..."):
        # Initialize agent
        agent = WorkoutAgent(
            api_key=api_key if auth_mode == "Google AI Studio (API Key)" else None,
            vertexai=(auth_mode == "Vertex AI (ADC)"),
            project=project if auth_mode == "Vertex AI (ADC)" else None,
            location=location,
            model_name=model_name,
            demo_mode=demo_mode
        )
        st.session_state.agent = agent

        # Generate plan
        result = agent.generate_plan(profile)
        st.session_state.workout_plan_result = result
        st.session_state.chat_messages = []

# Display Result if available
if st.session_state.workout_plan_result:
    result = st.session_state.workout_plan_result
    metrics = result.get("metrics", {})

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

    # Plan Markdown Tabs
    tab_plan, tab_export, tab_traces = st.tabs(["📋 Workout Routine", "💾 Export Plan", "🔍 Observability & Traces"])

    with tab_plan:
        st.markdown(result.get("plan_markdown", ""))

    with tab_export:
        st.subheader("Export Workout Plan")
        plan_text = result.get("plan_markdown", "")
        st.download_button(
            label="📥 Download Plan as Markdown (.md)",
            data=plan_text,
            file_name="fitforge_workout_plan.md",
            mime="text/markdown",
            use_container_width=True
        )

        import json
        st.download_button(
            label="📥 Download Full Profile & Metrics (.json)",
            data=json.dumps(result, indent=2),
            file_name="fitforge_profile_plan.json",
            mime="application/json",
            use_container_width=True
        )

    with tab_traces:
        st.subheader("Agent Execution Traces & Latencies")
        traces = result.get("trace_summary", {})
        st.write(f"**Total Execution Duration:** {traces.get('total_duration_ms', 0)} ms")
        st.write(f"**Recorded Steps / Tool Calls:** {traces.get('total_events', 0)}")
        st.json(traces.get("events", []))

    st.divider()

    # Interactive Chat with Coach Agent
    st.subheader("💬 Chat with your Coach Agent")
    st.caption("Ask questions, request exercise swaps (e.g. 'Swap squats for leg press'), or adjust volume.")

    # Display chat history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask Coach FitForge a question or request a change..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get coach response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if st.session_state.agent:
                    response = st.session_state.agent.chat(prompt)
                else:
                    response = "Agent session expired. Please regenerate your plan."
                st.markdown(response)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})

else:
    # Empty state prompt
    st.info("👈 Set your fitness goals and equipment in the sidebar and click **'Generate Workout Plan'** to start!")
    
    col_feat1, col_feat2, col_feat3 = st.columns(3)
    with col_feat1:
        st.markdown("### 🛠️ Deterministic Tools")
        st.markdown("- Mifflin-St Jeor BMR & TDEE calculation\n- Macronutrient partitioning\n- Curated exercise catalog with injury filters")
    with col_feat2:
        st.markdown("### 🧠 AI Coach Reasoning")
        st.markdown("- Built for Gemini 2.5 / Vertex AI\n- Multi-turn interactive adjustments\n- Progressive overload protocols")
    with col_feat3:
        st.markdown("### 🔍 Observability & CI")
        st.markdown("- Execution step latency tracing\n- Pytest automated test suite\n- Ready for GitHub submission")
