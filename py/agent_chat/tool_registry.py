import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional

from mcp_server.path_utils import find_repo_root

RiskLevel = Literal["read_only", "write", "dangerous", "external"]
ToolHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: ToolHandler
    risk_level: RiskLevel = "read_only"
    requires_confirmation: bool = False
    skill_name: Optional[str] = None


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        spec = self._tools.get(name)
        if spec is None:
            raise KeyError(name)
        return spec

    def has(self, name: str) -> bool:
        return name in self._tools

    def list(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "input_schema": spec.input_schema,
                "risk_level": spec.risk_level,
                "requires_confirmation": spec.requires_confirmation,
                "skill_name": spec.skill_name,
            }
            for spec in sorted(self._tools.values(), key=lambda item: item.name)
        ]


def register_workspace_tools(registry: ToolRegistry, workspace_root: Optional[Path] = None) -> None:
    root = workspace_root or find_repo_root(Path(__file__))

    registry.register(
        ToolSpec(
            name="read_file",
            description="Read a UTF-8 text file under the repository workspace.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_chars": {"type": "integer", "default": 12000},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            handler=lambda args: _read_file(root, args),
            risk_level="read_only",
        )
    )
    registry.register(
        ToolSpec(
            name="search_code",
            description="Search repository text with ripgrep.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "path": {"type": "string", "default": "."},
                    "max_results": {"type": "integer", "default": 40},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            handler=lambda args: _search_code(root, args),
            risk_level="read_only",
        )
    )
    registry.register(
        ToolSpec(
            name="write_file",
            description="Write UTF-8 text to a repository file. Requires user confirmation.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "overwrite": {"type": "boolean", "default": False},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
            handler=lambda args: _write_file(root, args),
            risk_level="write",
            requires_confirmation=True,
        )
    )
    registry.register(
        ToolSpec(
            name="run_command",
            description="Run a shell command in the repository. Requires user confirmation.",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "cwd": {"type": "string", "default": "."},
                    "timeout_ms": {"type": "integer", "default": 30000},
                },
                "required": ["command"],
                "additionalProperties": False,
            },
            handler=lambda args: _run_command(root, args),
            risk_level="dangerous",
            requires_confirmation=True,
        )
    )


def _read_file(root: Path, args: Dict[str, Any]) -> Dict[str, Any]:
    path = _resolve_inside(root, str(args.get("path") or ""))
    max_chars = int(args.get("max_chars") or 12000)
    content = path.read_text(encoding="utf-8", errors="replace")
    truncated = len(content) > max_chars
    return {
        "path": str(path.relative_to(root)),
        "content": content[:max_chars],
        "truncated": truncated,
        "size": len(content),
    }


def _search_code(root: Path, args: Dict[str, Any]) -> Dict[str, Any]:
    query = str(args.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")
    search_path = _resolve_inside(root, str(args.get("path") or "."))
    max_results = int(args.get("max_results") or 40)
    completed = subprocess.run(
        ["rg", "--line-number", "--no-heading", "--color", "never", query, str(search_path)],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    lines = completed.stdout.splitlines()[:max_results]
    return {
        "query": query,
        "path": str(search_path.relative_to(root)),
        "matches": lines,
        "count": len(lines),
        "exit_code": completed.returncode,
    }


def _write_file(root: Path, args: Dict[str, Any]) -> Dict[str, Any]:
    path = _resolve_inside(root, str(args.get("path") or ""))
    if path.exists() and not bool(args.get("overwrite")):
        raise ValueError("file exists; set overwrite=true")
    path.parent.mkdir(parents=True, exist_ok=True)
    content = str(args.get("content") or "")
    path.write_text(content, encoding="utf-8")
    return {"path": str(path.relative_to(root)), "bytes": len(content.encode("utf-8"))}


def _run_command(root: Path, args: Dict[str, Any]) -> Dict[str, Any]:
    command = str(args.get("command") or "").strip()
    if not command:
        raise ValueError("command is required")
    cwd = _resolve_inside(root, str(args.get("cwd") or "."))
    timeout_ms = int(args.get("timeout_ms") or 30000)
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=max(timeout_ms / 1000, 1),
        shell=True,
        check=False,
    )
    return {
        "command": command,
        "cwd": str(cwd.relative_to(root)),
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
    }


def _resolve_inside(root: Path, value: str) -> Path:
    if not value:
        raise ValueError("path is required")
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    if root.resolve() not in [resolved, *resolved.parents]:
        raise ValueError("path must stay inside repository workspace")
    return resolved
