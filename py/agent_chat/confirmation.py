import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Confirmation:
    id: str
    run_id: str
    session_id: str
    tool_name: str
    arguments: Dict[str, Any]
    risk_level: str
    input_summary: str
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0
    result: Optional[Dict[str, Any]] = None


class ConfirmationRequired(RuntimeError):
    def __init__(self, confirmation: Confirmation):
        super().__init__("Tool execution requires confirmation")
        self.confirmation = confirmation


class InMemoryConfirmationStore:
    def __init__(self, ttl_seconds: int = 900):
        self.ttl_seconds = ttl_seconds
        self._items: Dict[str, Confirmation] = {}

    def create(
            self,
            *,
            run_id: str,
            session_id: str,
            tool_name: str,
            arguments: Dict[str, Any],
            risk_level: str,
            input_summary: str,
    ) -> Confirmation:
        confirmation = Confirmation(
            id=f"confirmation_{uuid.uuid4().hex}",
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            arguments=arguments,
            risk_level=risk_level,
            input_summary=input_summary,
            expires_at=time.time() + self.ttl_seconds,
        )
        self._items[confirmation.id] = confirmation
        return confirmation

    def get(self, confirmation_id: str) -> Confirmation:
        confirmation = self._items.get(confirmation_id)
        if confirmation is None:
            raise ValueError("confirmation not found")
        if confirmation.status == "pending" and confirmation.expires_at < time.time():
            confirmation.status = "expired"
        return confirmation

    def approve(self, confirmation_id: str) -> Confirmation:
        confirmation = self.get(confirmation_id)
        if confirmation.status != "pending":
            raise ValueError(f"confirmation is {confirmation.status}")
        confirmation.status = "approved"
        return confirmation

    def reject(self, confirmation_id: str) -> Confirmation:
        confirmation = self.get(confirmation_id)
        if confirmation.status != "pending":
            raise ValueError(f"confirmation is {confirmation.status}")
        confirmation.status = "rejected"
        return confirmation

    def complete(self, confirmation_id: str, result: Dict[str, Any]) -> Confirmation:
        confirmation = self.get(confirmation_id)
        confirmation.status = "completed"
        confirmation.result = result
        return confirmation

    def list_pending(self, session_id: Optional[str] = None) -> List[Confirmation]:
        confirmations = []
        for item in self._items.values():
            if item.status == "pending" and item.expires_at < time.time():
                item.status = "expired"
            if item.status != "pending":
                continue
            if session_id and item.session_id != session_id:
                continue
            confirmations.append(item)
        return confirmations

    def dump(self, confirmation: Confirmation) -> Dict[str, Any]:
        return {
            "id": confirmation.id,
            "run_id": confirmation.run_id,
            "session_id": confirmation.session_id,
            "tool_name": confirmation.tool_name,
            "arguments": confirmation.arguments,
            "risk_level": confirmation.risk_level,
            "input_summary": confirmation.input_summary,
            "status": confirmation.status,
            "created_at": confirmation.created_at,
            "expires_at": confirmation.expires_at,
            "result": confirmation.result,
        }
