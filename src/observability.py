"""Observability, OpenTelemetry-compatible tracing, pre-execution intent logging, and structured JSON logging."""

import os
import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from contextlib import contextmanager

from src.pii import PIIRedactor


class SpanStatus(str, Enum):
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


class JSONLogFormatter(logging.Formatter):
    """Formats log records as structured JSON with trace correlation and PII redaction."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt) or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": PIIRedactor.redact_text(record.getMessage()),
            "module": record.module,
            "line": record.lineno,
            "trace_id": getattr(record, "trace_id", None),
            "span_id": getattr(record, "span_id", None),
            "component": getattr(record, "component", "fitforge_core"),
            "event_type": getattr(record, "event_type", "log")
        }
        if hasattr(record, "payload") and record.payload is not None:
            log_obj["payload"] = PIIRedactor.redact_data(record.payload)
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def configure_logging(level: int = logging.INFO, use_json: bool = True) -> logging.Logger:
    """Configure fitforge application logger."""
    root_logger = logging.getLogger("fitforge")
    root_logger.setLevel(level)

    # Clear existing handlers to prevent duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()

    handler = logging.StreamHandler()
    if use_json:
        handler.setFormatter(JSONLogFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    root_logger.addHandler(handler)
    return root_logger


logger = configure_logging()


@dataclass
class SpanEvent:
    """An event within a span (e.g. intent log, state change, error)."""
    name: str
    timestamp: float = field(default_factory=time.time)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """OpenTelemetry-compatible span for tracing agent workflows."""
    name: str
    trace_id: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_span_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    status: SpanStatus = SpanStatus.UNSET
    status_message: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = PIIRedactor.redact_data(value)

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        safe_attrs = PIIRedactor.redact_data(attributes or {})
        self.events.append(SpanEvent(name=name, attributes=safe_attrs))

    def set_status(self, status: SpanStatus, message: Optional[str] = None) -> None:
        self.status = status
        self.status_message = message

    def finish(self) -> None:
        if self.end_time is None:
            self.end_time = time.time()
            self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
            if self.status == SpanStatus.UNSET:
                self.status = SpanStatus.OK


@dataclass
class TraceEvent:
    """Records an individual execution step, intent, or tool call."""
    event_type: str  # 'intent', 'tool_call', 'agent_turn', 'plan_generation', 'guardrail_audit', 'hitl_request'
    name: str
    duration_ms: float
    input_data: Optional[Dict[str, Any]] = None
    output_summary: Optional[str] = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


class ExecutionTracer:
    """
    OpenTelemetry-compatible Tracer & Execution Logger with:
    - Pre-execution intent logging
    - OpenTelemetry Span hierarchy
    - PII Redaction
    - Structured JSON summaries
    """

    def __init__(self, trace_id: Optional[str] = None):
        self.trace_id: str = trace_id or uuid.uuid4().hex
        self.spans: List[Span] = []
        self.events: List[TraceEvent] = []
        self.start_time: float = time.time()
        self._current_span: Optional[Span] = None

    def log_intent(self, action: str, rationale: str, target_params: Optional[Dict[str, Any]] = None) -> None:
        """
        Log pre-execution intent before calling a tool, LLM, or sub-agent.
        Ensures intent is captured before any action occurs.
        """
        safe_params = PIIRedactor.redact_data(target_params or {})
        intent_event = TraceEvent(
            event_type="intent",
            name=f"intent:{action}",
            duration_ms=0.0,
            input_data={"rationale": rationale, "target_params": safe_params},
            output_summary=f"Intent declared: {rationale}",
            trace_id=self.trace_id,
            span_id=self._current_span.span_id if self._current_span else None
        )
        self.events.append(intent_event)
        logger.info(
            f"[INTENT] Action '{action}': {rationale}",
            extra={
                "trace_id": self.trace_id,
                "span_id": self._current_span.span_id if self._current_span else None,
                "event_type": "intent",
                "component": "tracer",
                "payload": {"action": action, "rationale": rationale, "params": safe_params}
            }
        )

    @contextmanager
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create and enter a new OpenTelemetry-compatible span."""
        parent_id = self._current_span.span_id if self._current_span else None
        span = Span(
            name=name,
            trace_id=self.trace_id,
            parent_span_id=parent_id,
            attributes=PIIRedactor.redact_data(attributes or {})
        )
        self.spans.append(span)
        previous_span = self._current_span
        self._current_span = span
        try:
            yield span
            span.finish()
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            span.finish()
            raise
        finally:
            self._current_span = previous_span

    def record_event(
        self,
        event_type: str,
        name: str,
        duration_ms: float,
        input_data: Optional[Dict[str, Any]] = None,
        output_summary: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Record a completed execution event with PII redaction."""
        safe_input = PIIRedactor.redact_data(input_data)
        safe_output = PIIRedactor.redact_text(output_summary) if output_summary else None
        safe_error = PIIRedactor.redact_text(error) if error else None

        event = TraceEvent(
            event_type=event_type,
            name=name,
            duration_ms=round(duration_ms, 2),
            input_data=safe_input,
            output_summary=safe_output,
            error=safe_error,
            trace_id=self.trace_id,
            span_id=self._current_span.span_id if self._current_span else None
        )
        self.events.append(event)

        extra = {
            "trace_id": self.trace_id,
            "span_id": self._current_span.span_id if self._current_span else None,
            "event_type": event_type,
            "component": "execution_tracer",
            "payload": {"duration_ms": duration_ms, "input": safe_input, "output": safe_output}
        }
        if error:
            logger.error(f"[{event_type}] {name} failed in {duration_ms:.1f}ms: {safe_error}", extra=extra)
        else:
            logger.info(f"[{event_type}] {name} completed in {duration_ms:.1f}ms", extra=extra)

    def get_summary(self) -> Dict[str, Any]:
        """Return structured summary of spans, intent logs, and trace events."""
        total_time_ms = round((time.time() - self.start_time) * 1000, 2)
        return {
            "trace_id": self.trace_id,
            "total_events": len(self.events),
            "total_spans": len(self.spans),
            "total_duration_ms": total_time_ms,
            "events": [asdict(e) for e in self.events],
            "spans": [
                {
                    "name": s.name,
                    "span_id": s.span_id,
                    "parent_span_id": s.parent_span_id,
                    "duration_ms": s.duration_ms,
                    "status": s.status.value,
                    "attributes": s.attributes,
                    "events_count": len(s.events)
                }
                for s in self.spans
            ]
        }
