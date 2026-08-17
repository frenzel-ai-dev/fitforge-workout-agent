"""Simple observability, execution tracing, and structured logging."""

import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

# Configure base logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("fitforge")


@dataclass
class TraceEvent:
    """Records an individual execution step or tool call."""
    event_type: str  # 'agent_turn', 'tool_call', 'plan_generation'
    name: str
    duration_ms: float
    input_data: Optional[Dict[str, Any]] = None
    output_summary: Optional[str] = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class ExecutionTracer:
    """Lightweight tracer for recording latency, tool invocations, and session metrics."""

    def __init__(self):
        self.events: List[TraceEvent] = []
        self.start_time: float = time.time()

    def record_event(
        self,
        event_type: str,
        name: str,
        duration_ms: float,
        input_data: Optional[Dict[str, Any]] = None,
        output_summary: Optional[str] = None,
        error: Optional[str] = None
    ):
        event = TraceEvent(
            event_type=event_type,
            name=name,
            duration_ms=round(duration_ms, 2),
            input_data=input_data,
            output_summary=output_summary,
            error=error
        )
        self.events.append(event)
        if error:
            logger.error(f"[{event_type}] {name} failed in {duration_ms:.1f}ms: {error}")
        else:
            logger.info(f"[{event_type}] {name} completed in {duration_ms:.1f}ms")

    def get_summary(self) -> Dict[str, Any]:
        """Return summary of total steps and duration."""
        total_time_ms = round((time.time() - self.start_time) * 1000, 2)
        return {
            "total_events": len(self.events),
            "total_duration_ms": total_time_ms,
            "events": [asdict(e) for e in self.events]
        }
