import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from agent_runtime.index import CODE_EXTENSIONS, IGNORED_DIRS, ProjectDocumentIndex
from agent_runtime.schemas import AgentRuntimeToolCall


@dataclass
class ToolResult:
    payload: Dict[str, Any]
    call: AgentRuntimeToolCall


@dataclass
class PendingConfirmation:
    confirmation_id: str
    command: str
    args: List[str]
    created_at: float


class ProjectToolbox:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.document_index = ProjectDocumentIndex(self.project_root)

    def build_index(self, max_files: int = 300, force: bool = False) -> Dict[str, int | bool]:
        return self.document_index.build(max_files=max_files, force=force)

    def timed(self, name: str, input_payload: Dict[str, Any], func: Callable, *args) -> ToolResult:
        started = time.perf_counter()
        try:
            payload = func(*args)
            status = "success"
            summary = self._summarize_tool_output(name, payload)
        except Exception as exc:
            payload = {"error": str(exc)}
            status = "failed"
            summary = str(exc)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ToolResult(
            payload=payload,
            call=AgentRuntimeToolCall(
                tool_name=name,
                input_payload=input_payload,
                output_summary=summary,
                status=status,
                latency_ms=latency_ms,
            ),
        )

    def overview(self) -> Dict[str, Any]:
        entries = []
        for child in sorted(self.project_root.iterdir(), key=lambda item: item.name.lower()):
            if child.name in IGNORED_DIRS:
                continue
            if child.is_dir():
                entries.append({"path": child.name, "type": "directory"})
            elif child.is_file() and child.suffix.lower() in CODE_EXTENSIONS:
                entries.append({"path": child.name, "type": "file"})

        important_files = []
        for relative in ["AGENTS.md", "pom.xml", "py/app.py", "py/bootstrap.py", "tool-hub/src/router/index.ts"]:
            path = self.project_root / relative
            if path.exists():
                important_files.append(relative)
        return {"entries": entries[:80], "important_files": important_files}

    def rag_retrieve(self, query: str, max_results: int) -> Dict[str, Any]:
        return {"query": query, "matches": self.document_index.search(query, max_results=max_results)}

    def search_project(self, query: str, max_results: int) -> Dict[str, Any]:
        query = query.strip()
        if not query:
            return {"query": query, "matches": []}

        try:
            completed = subprocess.run(
                [
                    "rg",
                    "--line-number",
                    "--no-heading",
                    "--color",
                    "never",
                    "--glob",
                    "!node_modules",
                    "--glob",
                    "!target",
                    "--glob",
                    "!dist",
                    "--glob",
                    "!build",
                    query,
                    str(self.project_root),
                ],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            if completed.returncode in (0, 1):
                return {"query": query, "matches": self._parse_rg_matches(completed.stdout, max_results)}
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return {"query": query, "matches": self._fallback_search(query, max_results)}

    def read_project_file(self, relative_path: str) -> Dict[str, Any]:
        path = self.resolve_safe_path(relative_path)
        if not path.exists() or not path.is_file():
            return {"path": relative_path, "found": False, "content": ""}
        text = path.read_text(encoding="utf-8", errors="replace")
        truncated = len(text) > 8000
        return {
            "path": self.relative(path),
            "found": True,
            "content": text[:8000],
            "truncated": truncated,
            "line_count": text.count("\n") + 1,
        }

    def split_command(self, command: str) -> List[str]:
        try:
            return [item.strip('"') for item in shlex.split(command, posix=False) if item.strip()]
        except ValueError:
            return command.split()

    def is_allowed_command(self, args: List[str]) -> Tuple[bool, str]:
        if not args:
            return False, "命令为空"
        lowered = [item.lower() for item in args]
        denied = {
            "rm",
            "del",
            "remove-item",
            "rmdir",
            "git reset",
            "git checkout",
            "git clean",
            "git push",
            "git commit",
            "docker",
        }
        joined = " ".join(lowered)
        if any(item in joined for item in denied):
            return False, "命令包含写入、删除、提交、推送或容器操作"

        executable = Path(lowered[0]).name
        if executable == "mvn":
            return ("test" in lowered or "package" in lowered), "仅允许 Maven test/package"
        if executable == "python":
            return (len(lowered) >= 3 and lowered[1] == "-m" and lowered[2] in {"unittest", "py_compile"}), \
                "仅允许 python -m unittest 或 python -m py_compile"
        if executable == "npm":
            return (lowered[1:3] == ["run", "build"] or lowered[1:2] == ["test"]), "仅允许 npm run build 或 npm test"
        if executable == "git":
            return (len(lowered) >= 2 and lowered[1] in {"status", "diff", "show", "log"}), \
                "仅允许 git status/diff/show/log"
        if executable == "rg":
            return True, "允许 rg 只读搜索"
        return False, "命令不在允许列表中"

    def run_confirmed_command(self, args: List[str]) -> Dict[str, Any]:
        completed = subprocess.run(
            args,
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        return {
            "exit_code": completed.returncode,
            "stdout": completed.stdout[:8000],
            "stderr": completed.stderr[:4000],
        }

    def resolve_safe_path(self, relative_path: str) -> Path:
        path = (self.project_root / relative_path).resolve()
        if path == self.project_root or self.project_root in path.parents:
            return path
        raise ValueError("path must stay inside project root")

    def relative(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.project_root)).replace("\\", "/")

    def _parse_rg_matches(self, output: str, max_results: int) -> List[Dict[str, Any]]:
        matches = []
        for line in output.splitlines():
            if len(matches) >= max_results:
                break
            path, line_number, snippet = self._split_rg_line(line)
            if not path:
                continue
            matches.append({"path": path, "line": line_number, "snippet": snippet.strip()[:240]})
        return matches

    def _split_rg_line(self, line: str) -> Tuple[str, int, str]:
        match = re.match(r"^(.+):(\d+):(.*)$", line)
        if not match:
            return "", 0, ""
        raw_path, raw_line, snippet = match.groups()
        try:
            line_number = int(raw_line)
        except ValueError:
            return "", 0, ""
        try:
            relative = self.relative(Path(raw_path))
        except ValueError:
            relative = raw_path
        return relative, line_number, snippet

    def _fallback_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        lowered = query.lower()
        matches = []
        for path in self.project_root.rglob("*"):
            if len(matches) >= max_results:
                break
            if not path.is_file() or path.suffix.lower() not in CODE_EXTENSIONS:
                continue
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            try:
                for index, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                    if lowered in line.lower():
                        matches.append({"path": self.relative(path), "line": index, "snippet": line.strip()[:240]})
                        break
            except OSError:
                continue
        return matches

    def _summarize_tool_output(self, name: str, payload: Dict[str, Any]) -> str:
        if name == "project_overview":
            return f"{len(payload.get('entries') or [])} entries"
        if name == "search_project":
            return f"{len(payload.get('matches') or [])} matches"
        if name == "rag_retrieve":
            return f"{len(payload.get('matches') or [])} chunks"
        if name == "read_project_file":
            return "found" if payload.get("found") else "not found"
        if name == "run_command":
            return f"exit_code={payload.get('exit_code')}"
        return "ok"
