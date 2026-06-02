import json
import re
import shlex
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from project_agent.rag import ProjectDocumentIndex
from project_agent.schemas import (
    ProjectAgentConfirmationResponse,
    ProjectAgentEvalCaseResult,
    ProjectAgentEvalRequest,
    ProjectAgentEvalResponse,
    ProjectAgentIndexResponse,
    ProjectAgentRequest,
    ProjectAgentResponse,
    ProjectAgentToolCall,
)


CODE_EXTENSIONS = {
    ".py",
    ".java",
    ".ts",
    ".tsx",
    ".js",
    ".vue",
    ".md",
    ".xml",
    ".yml",
    ".yaml",
    ".json",
    ".sql",
    ".toml",
    ".ini",
    ".properties",
}

IGNORED_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "target",
    "dist",
    "build",
    ".pytest_cache",
}


@dataclass
class ToolResult:
    payload: Dict[str, Any]
    call: ProjectAgentToolCall


@dataclass
class PendingConfirmation:
    confirmation_id: str
    command: str
    args: List[str]
    created_at: float


class ProjectAgentService:
    """Small project assistant agent with explicit tools and traceable decisions."""

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.document_index = ProjectDocumentIndex(self.project_root)
        self.sessions: Dict[str, List[Dict[str, str]]] = {}
        self.pending_confirmations: Dict[str, PendingConfirmation] = {}

    def chat(self, request: ProjectAgentRequest) -> ProjectAgentResponse:
        message = request.message.strip()
        if not message:
            raise ValueError("message is required")

        session_id = request.session_id or f"session_{uuid.uuid4().hex}"
        memory = self._session_history(session_id) + list(request.history or [])
        effective_message = self._with_memory_context(message, memory)
        tool_results: List[ToolResult] = []
        plan = self._plan(effective_message)

        if plan == "overview":
            tool_results.append(self._time_tool("project_overview", {}, self._project_overview))
        elif plan == "confirm_command":
            response = self._request_command_confirmation(message, session_id, memory)
            self._save_exchange(session_id, message, response.answer)
            return response
        elif plan == "read":
            paths = self._extract_paths(effective_message)
            if paths:
                for path in paths[:3]:
                    tool_results.append(self._time_tool("read_project_file", {"path": path}, self._read_project_file, path))
            else:
                query = self._extract_query(effective_message)
                tool_results.append(
                    self._time_tool("search_project", {"query": query, "max_results": request.max_results},
                                    self._search_project, query, request.max_results)
                )
        else:
            query = self._extract_query(effective_message)
            if request.use_rag:
                tool_results.append(
                    self._time_tool("rag_retrieve", {"query": query, "max_results": request.max_results},
                                    self._rag_retrieve, query, request.max_results)
                )
            tool_results.append(
                self._time_tool("search_project", {"query": query, "max_results": request.max_results},
                                self._search_project, query, request.max_results)
            )
            if self._should_add_overview(message, tool_results[-1].payload):
                tool_results.append(self._time_tool("project_overview", {}, self._project_overview))

        answer, citations = self._compose_answer(message, plan, tool_results)
        response = ProjectAgentResponse(
            answer=answer,
            session_id=session_id,
            citations=citations,
            tool_calls=[item.call for item in tool_results],
            structured_content={
                "plan": plan,
                "project_root": str(self.project_root),
                "evidence_count": len(citations),
                "memory_turns": len(memory),
            },
        )
        self._save_exchange(session_id, message, answer)
        return response

    def build_index(self, max_files: int = 300, force: bool = False) -> ProjectAgentIndexResponse:
        result = self.document_index.build(max_files=max_files, force=force)
        return ProjectAgentIndexResponse(**result)

    def stream_chat(self, request: ProjectAgentRequest) -> Iterable[str]:
        yield self._sse("step", {"node": "start", "status": "running"})
        response = self.chat(request)
        for call in response.tool_calls:
            yield self._sse(
                "tool_result",
                {
                    "tool_name": call.tool_name,
                    "status": call.status,
                    "summary": call.output_summary,
                    "latency_ms": call.latency_ms,
                },
            )
        yield self._sse("final", response.model_dump())

    def confirm(self, confirmation_id: str, approved: bool) -> ProjectAgentConfirmationResponse:
        pending = self.pending_confirmations.pop(confirmation_id, None)
        if pending is None:
            return ProjectAgentConfirmationResponse(
                confirmation_id=confirmation_id,
                status="not_found",
                answer="没有找到待确认操作，可能已经处理或已过期。",
            )
        if not approved:
            return ProjectAgentConfirmationResponse(
                confirmation_id=confirmation_id,
                status="rejected",
                answer=f"已取消执行：{pending.command}",
            )

        result = self._time_tool("run_command", {"command": pending.command}, self._run_confirmed_command,
                                pending.args)
        payload = result.payload
        output = payload.get("stdout") or payload.get("stderr") or ""
        answer = (
            f"命令已执行：`{pending.command}`\n"
            f"- exit_code: {payload.get('exit_code')}\n\n"
            f"```text\n{output[:4000]}\n```"
        )
        return ProjectAgentConfirmationResponse(
            confirmation_id=confirmation_id,
            status="executed",
            answer=answer,
            tool_call=result.call,
        )

    def run_eval_cases(self, payload: ProjectAgentEvalRequest) -> ProjectAgentEvalResponse:
        results: List[ProjectAgentEvalCaseResult] = []
        passed_count = 0
        for case in payload.cases:
            response = self.chat(
                ProjectAgentRequest(
                    message=case.message,
                    session_id=f"eval_{uuid.uuid4().hex}",
                    max_results=10,
                    use_rag=True,
                )
            )
            answer_blob = (response.answer + "\n" + "\n".join(response.citations)).lower()
            matched_terms = [item for item in case.must_include if item.lower() in answer_blob]
            used_tools = {call.tool_name for call in response.tool_calls}
            matched_tools = [item for item in case.tool_must_include if item in used_tools]
            answer_score = 1.0 if not case.must_include else len(matched_terms) / len(case.must_include)
            tool_score = 1.0 if not case.tool_must_include else len(matched_tools) / len(case.tool_must_include)
            passed = answer_score >= 0.8 and tool_score >= 1.0
            if passed:
                passed_count += 1
            results.append(
                ProjectAgentEvalCaseResult(
                    name=case.name,
                    passed=passed,
                    answer_score=round(answer_score, 4),
                    tool_score=round(tool_score, 4),
                    reason=f"matched_terms={matched_terms}; matched_tools={matched_tools}",
                )
            )
        total = len(payload.cases)
        return ProjectAgentEvalResponse(total=total, passed=passed_count, failed=total - passed_count, results=results)

    def _plan(self, message: str) -> str:
        lowered = message.lower()
        if any(word in lowered for word in ["运行", "执行", "run command", "run "]):
            return "confirm_command"
        if any(word in lowered for word in ["结构", "概览", "overview", "modules", "目录", "有哪些模块"]):
            return "overview"
        if self._extract_paths(message) or any(word in lowered for word in ["读取", "打开", "read file", "看一下"]):
            return "read"
        return "search"

    def _rag_retrieve(self, query: str, max_results: int) -> Dict[str, Any]:
        return {"query": query, "matches": self.document_index.search(query, max_results=max_results)}

    def _project_overview(self) -> Dict[str, Any]:
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

    def _search_project(self, query: str, max_results: int) -> Dict[str, Any]:
        query = query.strip()
        if not query:
            return {"query": query, "matches": []}

        try:
            completed = subprocess.run(
                ["rg", "--line-number", "--no-heading", "--color", "never", "--glob", "!node_modules",
                 "--glob", "!target", "--glob", "!dist", "--glob", "!build", query, str(self.project_root)],
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

    def _read_project_file(self, relative_path: str) -> Dict[str, Any]:
        path = self._resolve_safe_path(relative_path)
        if not path.exists() or not path.is_file():
            return {"path": relative_path, "found": False, "content": ""}
        text = path.read_text(encoding="utf-8", errors="replace")
        truncated = len(text) > 8000
        return {
            "path": self._relative(path),
            "found": True,
            "content": text[:8000],
            "truncated": truncated,
            "line_count": text.count("\n") + 1,
        }

    def _time_tool(self, name: str, input_payload: Dict[str, Any], func, *args) -> ToolResult:
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
            call=ProjectAgentToolCall(
                tool_name=name,
                input_payload=input_payload,
                output_summary=summary,
                status=status,
                latency_ms=latency_ms,
            ),
        )

    def _compose_answer(
            self,
            message: str,
            plan: str,
            tool_results: List[ToolResult],
    ) -> Tuple[str, List[str]]:
        citations: List[str] = []
        parts = []

        for result in tool_results:
            payload = result.payload
            if result.call.tool_name == "project_overview":
                entries = payload.get("entries") or []
                important = payload.get("important_files") or []
                directories = [item["path"] for item in entries if item.get("type") == "directory"]
                files = [item["path"] for item in entries if item.get("type") == "file"]
                parts.append(
                    "项目概览\n"
                    f"- 主要目录：{', '.join(directories[:16]) or '未发现'}\n"
                    f"- 根目录文件：{', '.join(files[:10]) or '未发现'}\n"
                    f"- 关键入口：{', '.join(important) or '未发现'}"
                )
                citations.extend(important)
            elif result.call.tool_name == "rag_retrieve":
                matches = payload.get("matches") or []
                if matches:
                    lines = []
                    for match in matches[:5]:
                        citation = f"{match['path']}:{match['line']}"
                        citations.append(citation)
                        lines.append(f"- {citation}：{match['snippet']}")
                    parts.append("RAG 检索到的上下文：\n" + "\n".join(lines))
            elif result.call.tool_name == "search_project":
                matches = payload.get("matches") or []
                if matches:
                    lines = []
                    for match in matches:
                        citation = f"{match['path']}:{match['line']}"
                        citations.append(citation)
                        lines.append(f"- {citation}：{match['snippet']}")
                    parts.append("我在项目里找到这些相关位置：\n" + "\n".join(lines))
                else:
                    parts.append(f"没有搜索到直接匹配：`{payload.get('query', '')}`。可以换一个更具体的类名、接口名或关键词。")
            elif result.call.tool_name == "read_project_file":
                if payload.get("found"):
                    citations.append(payload["path"])
                    preview = self._trim_lines(payload.get("content", ""), 24)
                    suffix = "\n\n内容较长，已截断。" if payload.get("truncated") else ""
                    parts.append(f"{payload['path']} 内容摘要：\n```text\n{preview}\n```{suffix}")
                else:
                    parts.append(f"没有找到文件：`{payload.get('path', '')}`。")

        if not parts:
            parts.append("我没有拿到可用的项目证据。")

        lead = "这是基于本地项目工具调用得到的结果。"
        if plan == "search" and "怎么" in message:
            lead = "我先按关键词定位了代码位置，下面是可参考的项目证据。"
        return lead + "\n\n" + "\n\n".join(parts), list(dict.fromkeys(citations))

    def _request_command_confirmation(
            self,
            message: str,
            session_id: str,
            memory: List[Dict[str, str]],
    ) -> ProjectAgentResponse:
        command = self._extract_command(message)
        if not command:
            return ProjectAgentResponse(
                answer="我识别到你想执行命令，但没有提取到明确命令。请用代码块或“运行 xxx”的格式发送。",
                session_id=session_id,
                structured_content={"plan": "confirm_command", "memory_turns": len(memory)},
            )
        args = self._split_command(command)
        allowed, reason = self._is_allowed_command(args)
        if not allowed:
            return ProjectAgentResponse(
                answer=f"这个命令不会执行：`{command}`\n原因：{reason}",
                session_id=session_id,
                structured_content={
                    "plan": "confirm_command",
                    "requires_confirmation": False,
                    "blocked": True,
                    "reason": reason,
                    "memory_turns": len(memory),
                },
            )

        confirmation_id = f"confirm_{uuid.uuid4().hex}"
        self.pending_confirmations[confirmation_id] = PendingConfirmation(
            confirmation_id=confirmation_id,
            command=command,
            args=args,
            created_at=time.time(),
        )
        return ProjectAgentResponse(
            answer=(
                "需要人工确认后才能执行命令。\n"
                f"- confirmation_id: `{confirmation_id}`\n"
                f"- command: `{command}`\n"
                "- 风险：会在项目根目录启动本地进程，可能消耗时间或产生构建输出。"
            ),
            session_id=session_id,
            structured_content={
                "plan": "confirm_command",
                "requires_confirmation": True,
                "confirmation": {
                    "id": confirmation_id,
                    "action": "run_command",
                    "command": command,
                    "risk": "local_process",
                },
                "memory_turns": len(memory),
            },
        )

    def _extract_command(self, message: str) -> str:
        block = re.search(r"```(?:\w+)?\n([\s\S]*?)```", message)
        if block:
            return block.group(1).strip().splitlines()[0].strip()
        match = re.search(r"(?:运行|执行|run command|run)\s+(.+)$", message, re.IGNORECASE)
        if match:
            return match.group(1).strip().strip("`")
        return ""

    def _split_command(self, command: str) -> List[str]:
        try:
            return [item.strip('"') for item in shlex.split(command, posix=False) if item.strip()]
        except ValueError:
            return command.split()

    def _is_allowed_command(self, args: List[str]) -> Tuple[bool, str]:
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

    def _run_confirmed_command(self, args: List[str]) -> Dict[str, Any]:
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

    def _session_history(self, session_id: str) -> List[Dict[str, str]]:
        return list(self.sessions.get(session_id, []))

    def _save_exchange(self, session_id: str, user_message: str, assistant_answer: str) -> None:
        history = self.sessions.setdefault(session_id, [])
        history.extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_answer[:2000]},
            ]
        )
        self.sessions[session_id] = history[-20:]

    def _with_memory_context(self, message: str, memory: List[Dict[str, str]]) -> str:
        lowered = message.lower()
        if not memory or not any(word in lowered for word in ["刚才", "继续", "上一个", "previous", "last"]):
            return message
        recent_user = [item["content"] for item in memory if item.get("role") == "user"]
        if not recent_user:
            return message
        return recent_user[-1] + "\n" + message

    def _sse(self, event: str, payload: Dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def _extract_paths(self, message: str) -> List[str]:
        candidates = re.findall(r"[\w./\\-]+\.(?:py|java|ts|tsx|js|vue|md|xml|ya?ml|json|sql|properties)", message)
        return [item.replace("\\", "/").strip("./") for item in candidates if item.strip()]

    def _extract_query(self, message: str) -> str:
        text = re.sub(r"```[\s\S]*?```", " ", message)
        identifiers = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b", text)
        if identifiers:
            return " ".join(identifiers[:4])
        text = re.sub(r"[，。！？?：:；;、]", " ", text)
        words = [word for word in re.split(r"\s+", text.strip()) if word]
        stop_words = {
            "帮我",
            "查找",
            "搜索",
            "哪里",
            "在哪",
            "项目",
            "代码",
            "一下",
            "please",
            "find",
            "search",
            "where",
            "is",
            "the",
        }
        useful = [word for word in words if word.lower() not in stop_words]
        return " ".join(useful[:8]) if useful else message[:80]

    def _should_add_overview(self, message: str, search_payload: Dict[str, Any]) -> bool:
        if search_payload.get("matches"):
            return False
        return any(word in message.lower() for word in ["项目", "module", "模块", "入口", "api"])

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
            relative = self._relative(Path(raw_path))
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
                        matches.append({"path": self._relative(path), "line": index, "snippet": line.strip()[:240]})
                        break
            except OSError:
                continue
        return matches

    def _resolve_safe_path(self, relative_path: str) -> Path:
        path = (self.project_root / relative_path).resolve()
        if path == self.project_root or self.project_root in path.parents:
            return path
        raise ValueError("path must stay inside project root")

    def _relative(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.project_root)).replace("\\", "/")

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

    def _trim_lines(self, text: str, max_lines: int) -> str:
        lines = text.splitlines()
        return "\n".join(lines[:max_lines])
