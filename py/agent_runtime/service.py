import json
import re
import time
import uuid
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from agent_runtime.schemas import (
    AgentRuntimeConfirmationResponse,
    AgentRuntimeRequest,
    AgentRuntimeResponse,
)
from agent_runtime.tools import PendingConfirmation, ProjectToolbox, ToolResult


class AgentRuntimeService:
    """Traceable project agent runtime with explicit planning and tools."""

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.toolbox = ProjectToolbox(self.project_root)
        self.sessions: Dict[str, List[Dict[str, str]]] = {}
        self.pending_confirmations: Dict[str, PendingConfirmation] = {}

    def run(self, request: AgentRuntimeRequest) -> AgentRuntimeResponse:
        message = request.message.strip()
        if not message:
            raise ValueError("message is required")

        session_id = request.session_id or f"session_{uuid.uuid4().hex}"
        memory = self._session_history(session_id) + list(request.history or [])
        effective_message = self._with_memory_context(message, memory)
        plan = self._plan(effective_message)
        tool_results: List[ToolResult] = []

        if plan == "overview":
            tool_results.append(self.toolbox.timed("project_overview", {}, self.toolbox.overview))
        elif plan == "confirm_command":
            response = self._request_command_confirmation(message, session_id, memory)
            self._save_exchange(session_id, message, response.answer)
            return response
        elif plan == "read":
            paths = self._extract_paths(effective_message)
            if paths:
                for path in paths[:3]:
                    tool_results.append(
                        self.toolbox.timed("read_project_file", {"path": path}, self.toolbox.read_project_file, path)
                    )
            else:
                query = self._extract_query(effective_message)
                tool_results.append(
                    self.toolbox.timed(
                        "search_project",
                        {"query": query, "max_results": request.max_results},
                        self.toolbox.search_project,
                        query,
                        request.max_results,
                    )
                )
        else:
            query = self._extract_query(effective_message)
            if request.use_rag:
                tool_results.append(
                    self.toolbox.timed(
                        "rag_retrieve",
                        {"query": query, "max_results": request.max_results},
                        self.toolbox.rag_retrieve,
                        query,
                        request.max_results,
                    )
                )
            tool_results.append(
                self.toolbox.timed(
                    "search_project",
                    {"query": query, "max_results": request.max_results},
                    self.toolbox.search_project,
                    query,
                    request.max_results,
                )
            )
            if self._should_add_overview(message, tool_results[-1].payload):
                tool_results.append(self.toolbox.timed("project_overview", {}, self.toolbox.overview))

        answer, citations = self._compose_answer(message, plan, tool_results)
        response = AgentRuntimeResponse(
            answer=answer,
            session_id=session_id,
            citations=citations,
            tool_calls=[item.call for item in tool_results],
            structured_content={
                "plan": plan,
                "project_root": str(self.project_root),
                "evidence_count": len(citations),
                "memory_turns": len(memory),
                "next_actions": self._next_actions(plan, tool_results),
            },
        )
        self._save_exchange(session_id, message, answer)
        return response

    def build_index(self, max_files: int = 300, force: bool = False) -> Dict[str, int | bool]:
        return self.toolbox.build_index(max_files=max_files, force=force)

    def stream(self, request: AgentRuntimeRequest) -> Iterable[str]:
        yield self._sse("step", {"node": "start", "status": "running"})
        response = self.run(request)
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

    def confirm(self, confirmation_id: str, approved: bool) -> AgentRuntimeConfirmationResponse:
        pending = self.pending_confirmations.pop(confirmation_id, None)
        if pending is None:
            return AgentRuntimeConfirmationResponse(
                confirmation_id=confirmation_id,
                status="not_found",
                answer="没有找到待确认操作，可能已经处理或已过期。",
            )
        if not approved:
            return AgentRuntimeConfirmationResponse(
                confirmation_id=confirmation_id,
                status="rejected",
                answer=f"已取消执行：{pending.command}",
            )

        result = self.toolbox.timed("run_command", {"command": pending.command}, self.toolbox.run_confirmed_command,
                                    pending.args)
        payload = result.payload
        output = payload.get("stdout") or payload.get("stderr") or ""
        answer = (
            f"命令已执行：`{pending.command}`\n"
            f"- exit_code: {payload.get('exit_code')}\n\n"
            f"```text\n{output[:4000]}\n```"
        )
        return AgentRuntimeConfirmationResponse(
            confirmation_id=confirmation_id,
            status="executed",
            answer=answer,
            tool_call=result.call,
        )

    def _plan(self, message: str) -> str:
        lowered = message.lower()
        if any(word in lowered for word in ["运行", "执行", "run command", "run "]):
            return "confirm_command"
        if any(word in lowered for word in ["结构", "概览", "overview", "modules", "目录", "有哪些模块"]):
            return "overview"
        if self._extract_paths(message) or any(word in lowered for word in ["读取", "打开", "read file", "看一下"]):
            return "read"
        return "project_qa"

    def _compose_answer(self, message: str, plan: str, tool_results: List[ToolResult]) -> Tuple[str, List[str]]:
        citations: List[str] = []
        sections = []

        for result in tool_results:
            payload = result.payload
            if result.call.tool_name == "project_overview":
                entries = payload.get("entries") or []
                important = payload.get("important_files") or []
                directories = [item["path"] for item in entries if item.get("type") == "directory"]
                files = [item["path"] for item in entries if item.get("type") == "file"]
                sections.append(
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
                    sections.append("语义索引候选：\n" + "\n".join(lines))
            elif result.call.tool_name == "search_project":
                matches = payload.get("matches") or []
                if matches:
                    lines = []
                    for match in matches:
                        citation = f"{match['path']}:{match['line']}"
                        citations.append(citation)
                        lines.append(f"- {citation}：{match['snippet']}")
                    sections.append("代码搜索命中：\n" + "\n".join(lines))
                else:
                    sections.append(f"没有搜索到直接匹配：`{payload.get('query', '')}`。")
            elif result.call.tool_name == "read_project_file":
                if payload.get("found"):
                    citations.append(payload["path"])
                    preview = self._trim_lines(payload.get("content", ""), 24)
                    suffix = "\n\n内容较长，已截断。" if payload.get("truncated") else ""
                    sections.append(f"{payload['path']} 内容摘要：\n```text\n{preview}\n```{suffix}")
                else:
                    sections.append(f"没有找到文件：`{payload.get('path', '')}`。")

        if not sections:
            sections.append("我没有拿到可用的项目证据。")

        lead = "这是项目 Agent 基于本地工具调用得到的结果。"
        if plan == "project_qa" and any(word in message for word in ["怎么", "为什么", "如何"]):
            lead = "我先定位了相关代码证据，再给出判断。"
        return lead + "\n\n" + "\n\n".join(sections), list(dict.fromkeys(citations))

    def _request_command_confirmation(
            self,
            message: str,
            session_id: str,
            memory: List[Dict[str, str]],
    ) -> AgentRuntimeResponse:
        command = self._extract_command(message)
        if not command:
            return AgentRuntimeResponse(
                answer="我识别到你想执行命令，但没有提取到明确命令。请用代码块或“运行 xxx”的格式发送。",
                session_id=session_id,
                structured_content={"plan": "confirm_command", "memory_turns": len(memory)},
            )
        args = self.toolbox.split_command(command)
        allowed, reason = self.toolbox.is_allowed_command(args)
        if not allowed:
            return AgentRuntimeResponse(
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
        return AgentRuntimeResponse(
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

    def _sse(self, event: str, payload: Dict[str, object]) -> str:
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

    def _should_add_overview(self, message: str, search_payload: Dict[str, object]) -> bool:
        if search_payload.get("matches"):
            return False
        return any(word in message.lower() for word in ["项目", "module", "模块", "入口", "api"])

    def _next_actions(self, plan: str, tool_results: List[ToolResult]) -> List[str]:
        if plan == "overview":
            return ["选择一个模块继续追踪入口、路由或数据流。"]
        if any(result.call.status == "failed" for result in tool_results):
            return ["根据失败的工具调用补充更具体的文件名、类名或命令。"]
        if plan == "read":
            return ["基于已读取文件继续分析调用方、测试覆盖或修改点。"]
        return ["确认目标后可以继续生成修改计划、定位测试命令或草拟补丁。"]

    def _trim_lines(self, text: str, max_lines: int) -> str:
        lines = text.splitlines()
        return "\n".join(lines[:max_lines])
