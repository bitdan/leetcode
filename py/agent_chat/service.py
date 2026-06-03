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
        from mcp_server.leetcode_coach import run_leetcode_coach

        payload = self._extract_leetcode_payload(text)
        return run_leetcode_coach(
            title=payload["title"],
            problem_statement=payload["problem_statement"],
            constraints=payload["constraints"],
            examples=payload["examples"],
            code=payload["code"],
            language=payload["language"],
            user_question=payload["user_question"],
            mode=payload["mode"],
        )

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
        topic = text.strip()
        intent = self._classify_general_intent(topic)
        draft = self._draft_general_answer(topic, intent)
        corrections = self._review_general_answer(draft, intent)
        return {
            "draft": draft,
            "corrections": corrections,
            "trace": [
                {
                    "node": "classify_intent",
                    "input_summary": topic[:80],
                    "output_summary": intent,
                    "decision": "continue",
                    "latency_ms": 0,
                },
                {
                    "node": "draft_answer",
                    "input_summary": intent,
                    "output_summary": draft[:120],
                    "decision": "review",
                    "latency_ms": 0,
                },
                {
                    "node": "review_answer",
                    "input_summary": draft[:120],
                    "output_summary": f"{len(corrections)} corrections",
                    "decision": "final",
                    "latency_ms": 0,
                },
            ],
        }

    def _classify_general_intent(self, text: str) -> str:
        lowered = text.lower()
        if any(item in lowered for item in ["agent", "智能体", "代理", "tool calling", "工具调用"]):
            return "agent_architecture"
        if any(item in lowered for item in ["重构", "refactor", "架构", "设计"]):
            return "engineering_design"
        if any(item in lowered for item in ["排查", "debug", "bug", "失败"]):
            return "debugging"
        if any(item in lowered for item in ["总结", "文档", "说明"]):
            return "writing"
        return "general_planning"

    def _draft_general_answer(self, text: str, intent: str) -> str:
        if intent == "agent_architecture":
            return "\n".join(
                [
                    "实现 Agent 不要从“聊天接口”开始，而是先定义一个可执行的任务循环。",
                    "",
                    "推荐最小架构：",
                    "1. Intent Router：判断用户是在问答、查代码、改代码、跑命令还是生成报告。",
                    "2. Planner：把目标拆成 3 到 6 个可验证步骤，例如检索上下文、读取文件、生成方案、执行工具、验证结果。",
                    "3. Tool Registry：把能力做成明确工具，例如 search_code、read_file、apply_patch、run_test、query_db。",
                    "4. Executor：按计划调用工具，每一步记录输入、输出、耗时和错误。",
                    "5. Memory：保存会话上下文、项目索引、用户偏好和已确认的操作结果。",
                    "6. Guardrail：危险操作必须确认，写文件和运行命令要有白名单、路径限制和超时。",
                    "7. Evaluator：检查回答是否引用证据、是否完成目标、测试是否通过，失败时回到 Planner 修正。",
                    "",
                    "一个实用执行流可以是：用户请求 -> 路由 -> 制定计划 -> 检索/读文件 -> 生成补丁或答案 -> 运行验证 -> 输出总结。",
                    "",
                    "在这个项目里，下一步应该把 `agent_runtime` 继续升级：让 Planner 产出结构化步骤，Tool Registry 支持写补丁和跑测试，再把 trace 展示给前端而不是混进回答正文。",
                ]
            )
        if intent == "engineering_design":
            return (
                "建议先收敛目标和边界，再按模块拆分现状、目标结构、迁移步骤和验证方式。"
                "重构不要只移动文件，应该减少重复职责，并保留兼容层直到调用方迁移完成。"
            )
        if intent == "debugging":
            return (
                "建议先定位稳定复现路径，再收集错误栈、最近变更、输入数据和环境差异。"
                "优先验证最深层根因，不要停在包装异常或接口层症状。"
            )
        if intent == "writing":
            return "建议按背景、目标、关键结论、证据、后续动作组织内容，让读者先看到判断，再看细节。"
        return f"可以把问题拆成目标、约束、候选方案、验证标准四块处理。原始问题：{text[:120]}"

    def _review_general_answer(self, draft: str, intent: str) -> List[str]:
        corrections = []
        if not draft.strip():
            corrections.append("补充明确结论，避免返回空内容。")
        if len(draft.strip()) < 40:
            corrections.append("补充执行步骤或判断依据，让建议更可操作。")
        if intent in {"agent_architecture", "engineering_design", "debugging"} and "验证" not in draft:
            corrections.append("补充验证方式，确保方案可以被确认。")
        return corrections

    def _format_langgraph_answer(self, data: Dict[str, Any]) -> str:
        parts = [f"结果\n{data.get('draft', '')}"]
        corrections = data.get("corrections") or []
        if corrections:
            parts.append("改进建议\n" + self._numbered(corrections))
        return "\n\n".join(parts)

    def _numbered(self, values: List[Any]) -> str:
        if not values:
            return "1. 无"
        return "\n".join(f"{index + 1}. {value}" for index, value in enumerate(values))
