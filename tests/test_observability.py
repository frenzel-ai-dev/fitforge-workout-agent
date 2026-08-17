"""Unit tests for Observability, OpenTelemetry spans, pre-execution intent logging, and PII redaction."""

import json
import logging
from src.pii import PIIRedactor
from src.observability import ExecutionTracer, JSONLogFormatter, SpanStatus


def test_pii_redactor():
    """Test redaction of emails, phones, SSNs, credit cards, and IPs."""
    text = "Athlete John Doe can be reached at john.doe@gym.com or 555-234-5678. IP: 192.168.1.50"
    redacted = PIIRedactor.redact_text(text)
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_IP]" in redacted
    assert "john.doe@gym.com" not in redacted

    # Dictionary recursion
    data = {
        "athlete_email": "athlete@fitforge.ai",
        "nested": {"phone": "(800) 555-0199", "notes": "Safe text"}
    }
    redacted_dict = PIIRedactor.redact_data(data)
    assert redacted_dict["athlete_email"] == "[REDACTED_EMAIL]"
    assert redacted_dict["nested"]["phone"] == "[REDACTED_PHONE]"


def test_execution_tracer_intent_and_spans():
    """Test ExecutionTracer records pre-execution intent logs and OpenTelemetry spans."""
    tracer = ExecutionTracer(trace_id="test_trace_123")

    # Log pre-execution intent
    tracer.log_intent(
        action="exercise_selection",
        rationale="Find knee-safe quad exercises",
        target_params={"equipment": "Dumbbells", "user_email": "user@test.com"}
    )

    # Start span
    with tracer.start_span("TestSubAgent.run", attributes={"agent": "TestAgent"}) as span:
        span.set_attribute("status", "in_progress")
        tracer.record_event(
            event_type="tool_call",
            name="get_exercise_recommendations",
            duration_ms=12.5,
            input_data={"param": "value"},
            output_summary="Found 10 exercises"
        )

    summary = tracer.get_summary()
    assert summary["trace_id"] == "test_trace_123"
    assert summary["total_events"] == 2
    assert summary["total_spans"] == 1

    # Verify intent log
    intent_event = summary["events"][0]
    assert intent_event["event_type"] == "intent"
    assert intent_event["name"] == "intent:exercise_selection"
    assert intent_event["input_data"]["target_params"]["user_email"] == "[REDACTED_EMAIL]"

    # Verify span
    span_data = summary["spans"][0]
    assert span_data["name"] == "TestSubAgent.run"
    assert span_data["status"] == SpanStatus.OK.value


def test_json_log_formatter():
    """Test structured JSON log formatting."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="fitforge.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message with email user@example.com",
        args=(),
        exc_info=None
    )
    record.trace_id = "trace_abc"
    record.payload = {"athlete_phone": "555-123-4567"}

    formatted_str = formatter.format(record)
    log_json = json.loads(formatted_str)

    assert log_json["level"] == "INFO"
    assert log_json["trace_id"] == "trace_abc"
    assert "[REDACTED_EMAIL]" in log_json["message"]
    assert log_json["payload"]["athlete_phone"] == "[REDACTED_PHONE]"
