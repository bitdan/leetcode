import re
from typing import Any, Dict, List, Literal, TypedDict

from mcp_server.java_stacktrace import analyze_java_stacktrace
from mcp_server.sql_generator import generate_nl_sql
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(..., description="User free-form message")
    history: List[Dict[str, str]] = Field(default_factory=list)


class AgentChatResponse(BaseModel):
    route: str
    title: str
    answer: str
    structured_content: Dict[str, Any]


class RouteDecision(TypedDict):
    route: Literal["leetcode_coach", "java_stacktrace", "nl_to_sql", "langgraph"]
    reason: str


class AgentChatService:
    def chat(self, request: AgentChatRequest) -> AgentChatResponse:
        text = request.message.strip()
        if not text:
            raise ValueError("message is required")
        decision = self._route(text)
        if decision["route"] == "leetcode_coach":
            structured = self._handle_leetcode(text)
            answer = self._format_leetcode_answer(structured)
            title = "LeetCode 陪练"
        elif decision["route"] == "java_stacktrace":
            structured = self._handle_stacktrace(text)
            answer = self._format_stacktrace_answer(structured)
            title = "Java 堆栈诊断"
        elif decision["route"] == "nl_to_sql":
            structured = self._handle_nl_to_sql(text)
            answer = self._format_nl_to_sql_answer(structured)
            title = "NL To SQL"
        else:
            structured = self._handle_langgraph(text)
            answer = self._format_langgraph_answer(structured)
            title = "通用工作流"
        structured["route_reason"] = decision["reason"]
        return AgentChatResponse(route=decision["route"], title=title, answer=answer, structured_content=structured)

    def _route(self, text: str) -> RouteDecision:
        lowered = text.lower()
        if self._looks_like_java_stacktrace(text):
            return {"route": "java_stacktrace", "reason": "Detected stacktrace patterns and Java exception markers."}
        if self._looks_like_leetcode_request(lowered):
            return {"route": "leetcode_coach",
                    "reason": "Detected LeetCode/problem-solving request with coding context."}
        if self._looks_like_sql_request(lowered):
            return {"route": "nl_to_sql", "reason": "Detected analytics-to-SQL style request."}
        return {"route": "langgraph", "reason": "No specialized skill matched, using general workflow."}

    def _looks_like_java_stacktrace(self, text: str) -> bool:
        markers = ["exception", "caused by:", "\nat ", "springframework", ".java:", "nullpointerexception"]
        lowered = text.lower()
        return sum(1 for item in markers if item in lowered) >= 2

    def _looks_like_leetcode_request(self, lowered: str) -> bool:
        markers = ["leetcode", "力扣", "题目", "题解", "时间复杂度", "空间复杂度", "怎么优化", "给定一个",
                   "given an array", "class solution", "public int", "public boolean"]
        return sum(1 for item in markers if item in lowered) >= 2

    def _looks_like_sql_request(self, lowered: str) -> bool:
        markers = ["sql", "销量最高", "近30天", "近7天", "sku", "account", "站点", "下单量", "订单"]
        return sum(1 for item in markers if item in lowered) >= 2

    def _handle_leetcode(self, text: str) -> Dict[str, Any]:
        from skill_adapters.leetcode_coach import run_leetcode_coach

        return run_leetcode_coach(self._extract_leetcode_payload(text))

    def _extract_leetcode_payload(self, text: str) -> Dict[str, Any]:
        code = self._extract_code_block(text)
        non_code_text = re.sub(r"```[\s\S]*?```", "", text).strip()
        lines = [line.strip() for line in non_code_text.splitlines() if line.strip()]
        title = lines[0] if lines else "LeetCode Problem"
        if len(title) > 120:
            title = "LeetCode Problem"
        lowered = text.lower()
        mode = "hint"
        if "review" in lowered or "帮我review" in text or "代码评审" in text:
            mode = "review"
        elif "teach" in lowered or "讲解" in text or "教我" in text:
            mode = "teach"
        elif "mock" in lowered or "面试" in text:
            mode = "mock"
        return {
            "title": title,
            "problem_statement": non_code_text or "Please analyze the provided LeetCode problem and user code.",
            "constraints": self._extract_section_lines(text, ["constraints", "约束"]),
            "examples": self._extract_section_lines(text, ["example", "示例"]),
            "code": code or "// No code block provided by user.",
            "language": self._infer_language(code or text),
            "user_question": lines[-1] if len(lines) > 1 else "",
            "mode": mode,
        }

    def _extract_code_block(self, text: str) -> str:
        match = re.search(r"```(?:\w+)?\n([\s\S]*?)```", text)
        if match:
            return match.group(1).strip()
        if "class Solution" in text:
            return text[text.index("class Solution"):].strip()
        return ""

    def _extract_section_lines(self, text: str, names: List[str]) -> List[str]:
        lines = [line.rstrip() for line in text.splitlines()]
        collected: List[str] = []
        active = False
        for line in lines:
            stripped = line.strip()
            lower = stripped.lower().rstrip(":")
            if any(name in lower for name in names):
                active = True
                continue
            if active:
                if not stripped:
                    if collected:
                        break
                    continue
                if re.match(r"^[A-Za-z\u4e00-\u9fa5].{0,20}:$", stripped):
                    break
                collected.append(stripped.lstrip("- ").strip())
        return collected[:5]

    def _infer_language(self, text: str) -> str:
        lowered = text.lower()
        if "public class" in lowered or "class solution" in lowered:
            return "java"
        if "def " in lowered:
            return "python"
        if "function " in lowered or "const " in lowered:
            return "javascript"
        return "java"

    def _format_leetcode_answer(self, data: Dict[str, Any]) -> str:
        return "\n\n".join(
            [
                f"题意理解\n{data.get('understanding', '')}",
                "关键观察\n" + self._numbered(data.get("key_observations", [])),
                f"提示\n{data.get('hint', '')}",
                f"复杂度分析\n{data.get('complexity_analysis', '')}",
                "代码评审\n" + self._numbered(data.get("review_findings", [])),
                f"下一步建议\n{data.get('next_step', '')}",
                "相似模式\n" + self._numbered(data.get("similar_patterns", [])),
            ]
        )

    def _handle_stacktrace(self, text: str) -> Dict[str, Any]:
        return analyze_java_stacktrace(stacktrace=text, context="Auto-routed from chat agent")

    def _format_stacktrace_answer(self, data: Dict[str, Any]) -> str:
        return "\n\n".join(
            [
                f"根因\n{data.get('root_cause', '')}",
                "证据\n" + self._numbered(data.get("evidence", [])),
                "修复建议\n" + self._numbered(data.get("likely_fixes", [])),
                "缺失上下文\n" + self._numbered(data.get("missing_context", [])),
            ]
        )

    def _handle_nl_to_sql(self, text: str) -> Dict[str, Any]:
        account_match = re.search(r"\b([A-Z]{2,}-[A-Z]{2,})\b", text)
        return generate_nl_sql(question=text, account=account_match.group(1) if account_match else "")

    def _format_nl_to_sql_answer(self, data: Dict[str, Any]) -> str:
        parts = [f"说明\n{data.get('explanation', '')}", f"SQL\n{data.get('preview_sql') or data.get('sql', '')}"]
        if data.get("result_columns"):
            parts.append("结果列\n" + self._numbered(data["result_columns"]))
        if data.get("tables"):
            parts.append("涉及表\n" + self._numbered(data["tables"]))
        return "\n\n".join(parts)

    def _handle_langgraph(self, text: str) -> Dict[str, Any]:
        from workflow_adapter.langgraph_workflow import execute_langgraph_workflow

        return execute_langgraph_workflow(text)

    def _format_langgraph_answer(self, data: Dict[str, Any]) -> str:
        parts = [f"结果\n{data.get('draft', '')}"]
        corrections = data.get("corrections") or []
        if corrections:
            parts.append("改进建议\n" + self._numbered(corrections))
        trace = data.get("trace") or []
        if trace:
            trace_lines = [
                f"{index + 1}. {item.get('node')} | {item.get('input_summary')} -> {item.get('output_summary')} | decision={item.get('decision')} | {item.get('latency_ms')}ms"
                for index, item in enumerate(trace)
            ]
            parts.append("执行轨迹\n" + "\n".join(trace_lines))
        return "\n\n".join(parts)

    def _numbered(self, values: List[Any]) -> str:
        if not values:
            return "1. 无"
        return "\n".join(f"{index + 1}. {value}" for index, value in enumerate(values))
