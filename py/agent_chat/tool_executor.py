import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from agent_chat.confirmation import ConfirmationRequired, InMemoryConfirmationStore
from agent_chat.tool_registry import ToolRegistry, ToolSpec


@dataclass
class ToolExecution:
    tool_name: str
    arguments: Dict[str, Any]
    output: Dict[str, Any]
    status: str
    latency_ms: int
    error: Optional[str] = None


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, confirmations: InMemoryConfirmationStore):
        self.registry = registry
        self.confirmations = confirmations

    def execute(
            self,
            tool_name: str,
            arguments: Dict[str, Any],
            *,
            run_id: str,
            session_id: str,
            confirmed: bool = False,
    ) -> ToolExecution:
        spec = self.registry.get(tool_name)
        self._validate_arguments(spec, arguments)
        if spec.requires_confirmation and not confirmed:
            confirmation = self.confirmations.create(
                run_id=run_id,
                session_id=session_id,
                tool_name=tool_name,
                arguments=arguments,
                risk_level=spec.risk_level,
                input_summary=self._input_summary(arguments),
            )
            raise ConfirmationRequired(confirmation)

        started = time.perf_counter()
        try:
            output = spec.handler(arguments)
            status = "success"
            error = None
        except Exception as exc:
            output = {"error": str(exc)}
            status = "failed"
            error = str(exc)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ToolExecution(
            tool_name=tool_name,
            arguments=arguments,
            output=output,
            status=status,
            latency_ms=latency_ms,
            error=error,
        )

    def _validate_arguments(self, spec: ToolSpec, arguments: Dict[str, Any]) -> None:
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be an object")
        schema = spec.input_schema or {}
        required = schema.get("required") or []
        for key in required:
            if key not in arguments or arguments[key] in (None, ""):
                raise ValueError(f"{key} is required")
        if schema.get("additionalProperties") is False:
            allowed = set((schema.get("properties") or {}).keys())
            extra = set(arguments.keys()) - allowed
            if extra:
                raise ValueError(f"unexpected tool arguments: {', '.join(sorted(extra))}")

    def _input_summary(self, arguments: Dict[str, Any]) -> str:
        parts = []
        for key, value in arguments.items():
            text = str(value).replace("\n", " ")
            parts.append(f"{key}={text[:80]}")
        return "; ".join(parts)[:240]
