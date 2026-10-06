"""Execution trace: one event per tool action, written by the environment."""

import datetime


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class Tracer:
    """Collects events. The environment writes them; the model never does."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.events: list[dict] = []

    def log(
        self,
        *,
        tool: str,
        action: str,
        resource_id: str,
        authorization_class: str,
        outcome: str,
        **detail,
    ) -> dict:
        event = {
            "run_id": self.run_id,
            "seq": len(self.events) + 1,
            "timestamp": _now(),
            "event_type": "tool_call",
            "tool": tool,
            "action": action,
            "resource_id": resource_id,
            "authorization_class": authorization_class,
            "outcome": outcome,
        }
        if detail:
            event["detail"] = detail
        self.events.append(event)
        return event
