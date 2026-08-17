# 🏋️‍♂️ FitForge AI - Multi-Agent Workout Planning & Coaching System

An enterprise-grade, autonomous multi-agent fitness and workout planning system built with **Google Gemini**, **Vertex AI**, and deterministic exercise science tools.

FitForge AI combines specialized sub-agents, deterministic physiological algorithms, persistent SQLite memory with history compaction, OpenTelemetry tracing with pre-execution intent logging, automated safety guardrails, and Human-in-the-Loop (HITL) approval workflows.

---

## 🏗️ Architecture

```mermaid
graph TD
    User(["Athlete / User"]) <--> StreamlitUI["Streamlit Web UI (app.py)"]
    StreamlitUI <--> HITL["HITL Approval Manager (src/hitl.py)"]
    HITL <--> Coordinator["Coordinator / Router Agent (src/orchestrator.py)"]

    subgraph "Specialized Sub-Agents (Multi-Agent)"
        NutritionAgent["Nutrition Specialist (Gemini 2.5 Flash)"]
        ExerciseAgent["Exercise Specialist (Gemini 2.5 Flash)"]
        PeriodizationAgent["Periodization Specialist (Gemini 2.5 Pro)"]
        GuardrailAgent["Safety & Contraindication Auditor"]
    end

    subgraph "Deterministic Tools & Function Calling (src/tools.py)"
        BMRTool["BMR / TDEE / Macro Calculator"]
        ExerciseTool["Curated Exercise Catalog"]
        SafetyTool["Exercise Safety & Contraindication Verifier"]
        OneRMTool["1RM & Intensity Calculator"]
        HRZonesTool["Heart Rate Zone Calculator"]
    end

    subgraph "Context & Memory Layer (src/memory.py)"
        SQLiteDB[("Persistent SQLite Store")]
        Compactor["History Compactor & Fact Extractor"]
    end

    subgraph "Observability & Security (src/observability.py & src/pii.py)"
        OTEL["OpenTelemetry Tracing & Intent Spans"]
        JSONLogger["Structured JSON Logging"]
        PIIRedactor["PII Redaction Engine"]
    end

    subgraph "Infrastructure & CI/CD"
        GoldenEvals["Golden Dataset Benchmark (evals/)"]
        TerraformIaC["Terraform Cloud Run & Secret Manager"]
        GitHubCI["GitHub Actions CI Pipeline"]
    end

    Coordinator --> NutritionAgent
    Coordinator --> ExerciseAgent
    Coordinator --> PeriodizationAgent
    Coordinator --> GuardrailAgent

    NutritionAgent --> BMRTool
    ExerciseAgent --> ExerciseTool
    ExerciseAgent --> SafetyTool
    ExerciseAgent --> OneRMTool

    Coordinator <--> SQLiteDB
    Coordinator <--> Compactor
    Coordinator -.-> OTEL
    Coordinator -.-> PIIRedactor
    Coordinator -.-> JSONLogger
```

---

## 🚀 Quickstart Guide

### 1. Clone & Setup Environment

```bash
# Clone the repository
git clone <your-repo-url>
cd <repo-folder>

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Authentication & Secrets

Create a `.env` file from the template:
```bash
cp .env.example .env
```

Supported authentication modes:
- **Google AI Studio API Key:** Set `GEMINI_API_KEY=your_key` in `.env` (or enter in UI sidebar).
- **Google Cloud Secret Manager / Vertex AI:** Set `GOOGLE_CLOUD_PROJECT=your_project_id` and authenticate via `gcloud auth application-default login`.
- **Demo / Mock Mode:** Built-in offline deterministic generator for testing without an API key.

### 3. Launch the Streamlit Web Application

```bash
streamlit run app.py
```

Access the UI at `http://localhost:8501`.

---

## 🧪 Running Tests & Evaluation Benchmarks

### 1. Run Pytest Suite
```bash
pytest tests/ -v
```

### 2. Run Automated Golden Dataset Evaluation Benchmark
```bash
python evals/evaluate.py
```

---

## 📁 Repository Structure

```
fitforge-workout-agent/
├── app.py                         # Streamlit Web Application with HITL modals & OTEL traces
├── requirements.txt               # Dependencies
├── .env.example                   # Environment variables template
├── cloudrun.yaml                  # Cloud Run service specification
├── Dockerfile                     # Production container image
├── docker-compose.yml             # Local container testing
├── .github/
│   └── workflows/
│       └── ci.yml                 # GitHub Actions CI/CD Pipeline
├── evals/
│   ├── __init__.py
│   ├── golden_dataset.json        # 10 Benchmark Athlete Scenarios
│   └── evaluate.py                # Evaluation runner scoring 5 rubric pillars
├── terraform/
│   ├── main.tf                    # Cloud Run, Secret Manager, & IAM IaC
│   ├── variables.tf               # Terraform variables
│   └── outputs.tf                 # Terraform outputs
├── src/
│   ├── __init__.py                # Package exports
│   ├── models.py                  # Pydantic schemas (UserProfile, WorkoutPlan, HITL, etc.)
│   ├── tools.py                   # Deterministic tools, JSON schemas, guided error recovery
│   ├── orchestrator.py            # Multi-agent coordination & dynamic model routing
│   ├── agent.py                   # Backwards-compatible WorkoutAgent interface
│   ├── memory.py                  # SQLite persistent storage & history compaction
│   ├── guardrails.py              # Input injection defense & output safety audit
│   ├── hitl.py                    # Human-in-the-Loop pause & approval engine
│   ├── pii.py                     # PII redaction engine
│   ├── observability.py           # OpenTelemetry tracing, intent logs, structured JSON logging
│   └── secrets.py                 # Google Cloud Secret Manager integration
└── tests/
    ├── __init__.py
    ├── test_models.py             # Schema and validator unit tests
    ├── test_tools.py              # Tool calculation & guided error recovery tests
    ├── test_agent.py              # Multi-agent pipeline & coordinator tests
    ├── test_memory.py             # SQLite persistence & compaction tests
    ├── test_guardrails.py         # Security guardrails & HITL tests
    ├── test_observability.py      # OTEL spans, intent logs, & PII redaction tests
    └── test_evals.py              # Golden dataset benchmark CI tests
```

---
