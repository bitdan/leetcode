import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from project_agent.schemas import ProjectAgentRequest, ProjectAgentResponse, ProjectAgentToolCall


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


class ProjectAgentService:
    """Small project assistant agent with explicit tools and traceable decisions."""

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()

    def chat(self, request: ProjectAgentRequest) -> ProjectAgentResponse:
        message = request.message.strip()
        if not message:
            raise ValueError("message is required")

        tool_results: List[ToolResult] = []
        plan = self._plan(message)

        if plan == "overview":
            tool_results.append(self._time_tool("project_overview", {}, self._project_overview))
        elif plan == "read":
            paths = self._extract_paths(message)
            if paths:
                for path in paths[:3]:
                    tool_results.append(self._time_tool("read_project_file", {"path": path}, self._read_project_file, path))
            else:
                query = self._extract_query(message)
                tool_results.append(
                    self._time_tool("search_project", {"query": query, "max_results": request.max_results},
                                    self._search_project, query, request.max_results)
                )
        else:
            query = self._extract_query(message)
            tool_results.append(
                self._time_tool("search_project", {"query": query, "max_results": request.max_results},
                                self._search_project, query, request.max_results)
            )
            if self._should_add_overview(message, tool_results[0].payload):
                tool_results.append(self._time_tool("project_overview", {}, self._project_overview))

        answer, citations = self._compose_answer(message, plan, tool_results)
        return ProjectAgentResponse(
            answer=answer,
            citations=citations,
            tool_calls=[item.call for item in tool_results],
            structured_content={
                "plan": plan,
                "project_root": str(self.project_root),
                "evidence_count": len(citations),
            },
        )

    def _plan(self, message: str) -> str:
        lowered = message.lower()
        if any(word in lowered for word in ["结构", "概览", "overview", "modules", "目录", "有哪些模块"]):
            return "overview"
        if self._extract_paths(message) or any(word in lowered for word in ["读取", "打开", "read file", "看一下"]):
            return "read"
        return "search"

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
        if name == "read_project_file":
            return "found" if payload.get("found") else "not found"
        return "ok"

    def _trim_lines(self, text: str, max_lines: int) -> str:
        lines = text.splitlines()
        return "\n".join(lines[:max_lines])
