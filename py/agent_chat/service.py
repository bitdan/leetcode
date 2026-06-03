import json
import re
import time
import uuid
from typing import Any, Dict, Iterable, List, Literal, Optional, TypedDict

from mcp_server.java_stacktrace import analyze_java_stacktrace
from mcp_server.sql_generator import generate_nl_sql
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(..., description="User free-form message")
    session_id: Optional[str] = None
    route: Optional[str] = Field(default="auto", description="auto or a supported agent route")
    history: List[Dict[str, str]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    options: Dict[str, Any] = Field(default_factory=dict)
    client_request_id: Optional[str] = None


class AgentChatStep(BaseModel):
    step_id: str
    node: str
    status: str
    input_summary: str = ""
    output_summary: str = ""
    latency_ms: int = 0
    error: Optional[str] = None
    tool_name: Optional[str] = None


class AgentChatToolCall(BaseModel):
    tool_name: str
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    output_summary: str = ""
    status: str = "success"
    latency_ms: int = 0
    error: Optional[str] = None


class AgentChatMetrics(BaseModel):
    latency_ms: int = 0
    steps_count: int = 0
    retry_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0


class AgentChatResponse(BaseModel):
    route: str
    title: str
    answer: str
    structured_content: Dict[str, Any]
    run_id: Optional[str] = None
    trace_id: Optional[str] = None
    session_id: Optional[str] = None
    status: str = "success"
    steps: List[AgentChatStep] = Field(default_factory=list)
    tool_calls: List[AgentChatToolCall] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    metrics: AgentChatMetrics = Field(default_factory=AgentChatMetrics)


class RouteDecision(TypedDict):
    route: Literal["leetcode_coach", "java_stacktrace", "nl_to_sql", "agent_architecture", "langgraph"]
    reason: str
    confidence: float
    missing_context: List[str]


class AgentChatError(RuntimeError):
    def __init__(self, error_code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.error_code = error_code
        self.retryable = retryable


class AgentChatService:
    ROUTE_TITLES = {
        "leetcode_coach": "LeetCode 陪练",
        "java_stacktrace": "Java 堆栈诊断",
        "nl_to_sql": "NL To SQL",
        "agent_architecture": "Agent 架构顾问",
        "langgraph": "通用工作流",
    }

    def __init__(self, openai_api_key: str = "", openai_api_base: str = "", model_name: str = "gpt-3.5-turbo"):
        self.openai_api_key = openai_api_key
        self.openai_api_base = openai_api_base
        self.model_name = model_name
        self._model_client = None

    def chat(self, request: AgentChatRequest) -> AgentChatResponse:
        return self._run(request)

    def stream(self, request: AgentChatRequest) -> Iterable[Dict[str, Any]]:
        state = self._new_state(request)
        try:
            text = self._normalize_message(request.message)
            decision = self._route(text, request)
            yield self._event("route_decided", {
                "route": decision["route"],
                "confidence": decision["confidence"],
                "reason": decision["reason"],
                "missing_context": decision["missing_context"],
                "trace_id": state["trace_id"],
                "run_id": state["run_id"],
                "session_id": state["session_id"],
            })
            plan = self._plan(text, decision)
            yield self._event("plan_created", {
                "route": decision["route"],
                "steps": plan,
                "trace_id": state["trace_id"],
                "run_id": state["run_id"],
            })
            response = self._execute_plan(request, text, decision, plan, state, emit=True)
            for call in response.tool_calls:
                yield self._event("tool_started", {
                    "tool_name": call.tool_name,
                    "input_payload": call.input_payload,
                    "trace_id": response.trace_id,
                    "run_id": response.run_id,
                })
                yield self._event("tool_finished", {
                    "tool_name": call.tool_name,
                    "status": call.status,
                    "output_summary": call.output_summary,
                    "latency_ms": call.latency_ms,
                    "error": call.error,
                    "trace_id": response.trace_id,
                    "run_id": response.run_id,
                })
            for chunk in self._answer_chunks(response.answer):
                yield self._event("answer_delta", {"delta": chunk, "trace_id": response.trace_id, "run_id": response.run_id})
            yield self._event("final", self._dump_model(response))
        except AgentChatError as exc:
            yield self._event("error", self._error_payload(exc, state))
        except Exception as exc:
            yield self._event(
                "error",
                self._error_payload(AgentChatError("agent_internal_error", "Agent 执行失败", retryable=True), state),
            )

    def _run(self, request: AgentChatRequest) -> AgentChatResponse:
        state = self._new_state(request)
        text = self._normalize_message(request.message)
        decision = self._route(text, request)
        plan = self._plan(text, decision)
        return self._execute_plan(request, text, decision, plan, state, emit=False)

    def _execute_plan(
            self,
            request: AgentChatRequest,
            text: str,
            decision: RouteDecision,
            plan: List[Dict[str, Any]],
            state: Dict[str, str],
            emit: bool,
    ) -> AgentChatResponse:
        started = time.perf_counter()
        steps: List[AgentChatStep] = [
            AgentChatStep(
                step_id=self._step_id(),
                node="route_decided",
                status="success",
                input_summary=text[:120],
                output_summary=decision["route"],
                latency_ms=0,
                tool_name="intent_router",
            ),
            AgentChatStep(
                step_id=self._step_id(),
                node="plan_created",
                status="success",
                input_summary=decision["route"],
                output_summary=f"{len(plan)} steps",
                latency_ms=0,
                tool_name="planner",
            ),
        ]
        if decision["confidence"] < 0.45:
            answer = "我还不能稳定判断该进入哪个任务流程。请补充目标类型、输入材料和期望输出。"
            structured = self._structured(state, decision, plan, steps, [], {"missing_context": decision["missing_context"]})
            return AgentChatResponse(
                route=decision["route"],
                title=self.ROUTE_TITLES[decision["route"]],
                answer=answer,
                structured_content=structured,
                run_id=state["run_id"],
                trace_id=state["trace_id"],
                session_id=state["session_id"],
                status="needs_input",
                steps=steps,
                metrics=AgentChatMetrics(latency_ms=self._elapsed_ms(started), steps_count=len(steps)),
            )
        if decision["missing_context"]:
            answer = self._missing_context_answer(decision)
            structured = self._structured(state, decision, plan, steps, [], {"missing_context": decision["missing_context"]})
            return AgentChatResponse(
                route=decision["route"],
                title=self.ROUTE_TITLES[decision["route"]],
                answer=answer,
                structured_content=structured,
                run_id=state["run_id"],
                trace_id=state["trace_id"],
                session_id=state["session_id"],
                status="needs_input",
                steps=steps,
                metrics=AgentChatMetrics(latency_ms=self._elapsed_ms(started), steps_count=len(steps)),
            )

        tool_started = time.perf_counter()
        tool_name = self._tool_name(decision["route"])
        try:
            structured, answer = self._dispatch_route(decision["route"], text)
            status = "success"
            error = None
        except Exception as exc:
            structured = {"error": str(exc)}
            answer = "任务处理失败，请补充上下文后重试。"
            status = "failed"
            error = str(exc)
        tool_latency = self._elapsed_ms(tool_started)
        tool_call = AgentChatToolCall(
            tool_name=tool_name,
            input_payload={"message": text[:1000], "route": decision["route"]},
            output_summary=self._output_summary(structured, answer),
            status=status,
            latency_ms=tool_latency,
            error=error,
        )
        steps.append(
            AgentChatStep(
                step_id=self._step_id(),
                node="tool_finished",
                status=status,
                input_summary=tool_name,
                output_summary=tool_call.output_summary,
                latency_ms=tool_latency,
                error=error,
                tool_name=tool_name,
            )
        )
        eval_started = time.perf_counter()
        evaluation = self._evaluate_answer(answer, status)
        steps.append(
            AgentChatStep(
                step_id=self._step_id(),
                node="evaluate_response",
                status="success",
                input_summary=status,
                output_summary=evaluation["summary"],
                latency_ms=self._elapsed_ms(eval_started),
                tool_name="evaluator",
            )
        )
        structured.update(self._structured(state, decision, plan, steps, [tool_call], {"evaluation": evaluation}))
        return AgentChatResponse(
            route=decision["route"],
            title=self.ROUTE_TITLES[decision["route"]],
            answer=answer,
            structured_content=structured,
            run_id=state["run_id"],
            trace_id=state["trace_id"],
            session_id=state["session_id"],
            status=status,
            steps=steps,
            tool_calls=[tool_call],
            metrics=AgentChatMetrics(latency_ms=self._elapsed_ms(started), steps_count=len(steps)),
        )

    def _dispatch_route(self, route: str, text: str) -> tuple[Dict[str, Any], str]:
        if route == "leetcode_coach":
            structured = self._handle_leetcode(text)
            return structured, self._format_leetcode_answer(structured)
        if route == "java_stacktrace":
            structured = self._handle_stacktrace(text)
            structured["deepest_cause"] = self._deepest_caused_by(text)
            return structured, self._format_stacktrace_answer(structured)
        if route == "nl_to_sql":
            structured = self._handle_nl_to_sql(text)
            return structured, self._format_nl_to_sql_answer(structured)
        if route == "agent_architecture":
            structured = self._handle_agent_architecture(text)
            return structured, self._format_agent_architecture_answer(structured)
        structured = self._handle_langgraph(text)
        return structured, self._format_langgraph_answer(structured)

    def _normalize_message(self, message: str) -> str:
        text = message.strip()
        if not text:
            raise AgentChatError("agent_empty_message", "message is required", retryable=False)
        return text

    def _route(self, text: str, request: Optional[AgentChatRequest] = None) -> RouteDecision:
        forced_route = (request.route if request else "auto") or "auto"
        if forced_route != "auto" and forced_route in self.ROUTE_TITLES:
            decision = self._route_by_text(text)
            return {
                "route": forced_route,  # type: ignore[typeddict-item]
                "reason": "Route was explicitly requested by client.",
                "confidence": max(0.75, decision["confidence"]),
                "missing_context": self._missing_context(forced_route, text, request.context if request else {}),
            }
        model_decision = self._route_with_model(text, request.context if request else {})
        if model_decision:
            return model_decision
        return self._route_by_text(text, request.context if request else {})

    def _route_by_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> RouteDecision:
        lowered = text.lower()
        if self._looks_like_java_stacktrace(text):
            return {"route": "java_stacktrace", "reason": "Detected stacktrace patterns and Java exception markers.",
                    "confidence": 0.95, "missing_context": []}
        if self._looks_like_leetcode_request(lowered):
            return {"route": "leetcode_coach",
                    "reason": "Detected LeetCode/problem-solving request with coding context.",
                    "confidence": 0.88, "missing_context": []}
        if self._looks_like_sql_request(lowered):
            return {"route": "nl_to_sql", "reason": "Detected analytics-to-SQL style request.",
                    "confidence": 0.86, "missing_context": self._missing_context("nl_to_sql", text, context or {})}
        if self._looks_like_agent_architecture_request(lowered):
            return {"route": "agent_architecture", "reason": "Detected agent architecture or tool-calling request.",
                    "confidence": 0.85, "missing_context": []}
        if self._looks_like_general_question(lowered):
            return {"route": "langgraph", "reason": "Detected general knowledge or assistant question.",
                    "confidence": 0.6, "missing_context": []}
        if any(item in lowered for item in ["总结", "文档", "说明", "重构", "refactor", "架构", "设计", "debug", "bug", "失败"]):
            return {"route": "langgraph", "reason": "Detected general planning or writing request.",
                    "confidence": 0.55, "missing_context": []}
        if len(lowered.strip()) <= 2:
            return {"route": "langgraph", "reason": "The request is too short to route confidently.",
                    "confidence": 0.35, "missing_context": ["goal"]}
        return {"route": "langgraph", "reason": "No specialized skill matched, using model-backed general workflow.",
                "confidence": 0.55, "missing_context": []}

    def _missing_context(self, route: str, text: str, context: Dict[str, Any]) -> List[str]:
        if route != "nl_to_sql":
            return []
        if context.get("schema") or "create table" in text.lower() or "表结构" in text:
            return []
        return ["schema"]

    def _plan(self, text: str, decision: RouteDecision) -> List[Dict[str, Any]]:
        return [
            {"node": "intent_router", "summary": decision["reason"]},
            {"node": "planner", "summary": f"Use {decision['route']} handler"},
            {"node": self._tool_name(decision["route"]), "summary": "Run selected task tool"},
            {"node": "evaluator", "summary": "Check answer completeness and safety"},
        ]

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

    def _looks_like_agent_architecture_request(self, lowered: str) -> bool:
        markers = ["agent", "智能体", "代理", "tool calling", "工具调用", "planner", "executor"]
        return any(item in lowered for item in markers)

    def _looks_like_general_question(self, lowered: str) -> bool:
        markers = ["天气", "温度", "下雨", "晴天", "weather", "如何", "怎么样", "怎么", "是什么", "为什么"]
        return any(item in lowered for item in markers)

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

    def _handle_agent_architecture(self, text: str) -> Dict[str, Any]:
        goal = text.strip()
        components = [
            {"name": "Intent Router", "purpose": "识别用户是在问答、查代码、改代码、跑命令、查数据库还是生成报告。"},
            {"name": "Planner", "purpose": "把目标拆成少量可验证步骤，并决定每一步需要哪些工具和证据。"},
            {"name": "Tool Registry", "purpose": "用统一 schema 暴露 search_code、read_file、apply_patch、run_test、query_db 等工具。"},
            {"name": "Executor", "purpose": "按计划调用工具，记录输入、输出、错误、耗时和重试。"},
            {"name": "Memory", "purpose": "保存会话上下文、项目索引、用户偏好、已确认操作和历史结论。"},
            {"name": "Guardrail", "purpose": "限制危险命令、跨目录写入、未确认修改和长时间任务。"},
            {"name": "Evaluator", "purpose": "检查是否完成目标、是否引用证据、验证是否通过，失败时回到 Planner 修正。"},
        ]
        flow = [
            "接收用户目标并生成 intent",
            "检索项目或业务上下文",
            "生成结构化 plan",
            "逐步调用工具并记录 trace",
            "根据工具结果产出回答、补丁或报告",
            "运行验证并给出风险与下一步",
        ]
        return {
            "goal": goal,
            "summary": "实现 Agent 的核心不是聊天，而是一个带工具、状态、验证和安全边界的任务执行循环。",
            "components": components,
            "flow": flow,
            "implementation_hint": (
                "当前 Agent 工作台可以继续把 Planner、Tool Registry、Executor、Evaluator 做成独立类；"
                "前端只展示 answer，把 trace、tool_calls、citations 放到调试面板。"
            ),
            "trace": [
                {
                    "node": "detect_agent_architecture",
                    "input_summary": goal[:80],
                    "output_summary": "agent_architecture",
                    "decision": "specialized_route",
                    "latency_ms": 0,
                },
                {
                    "node": "compose_agent_blueprint",
                    "input_summary": "components+flow",
                    "output_summary": "7 components, 6 flow steps",
                    "decision": "final",
                    "latency_ms": 0,
                },
            ],
        }

    def _format_agent_architecture_answer(self, data: Dict[str, Any]) -> str:
        component_lines = [
            f"{index + 1}. {item['name']}：{item['purpose']}"
            for index, item in enumerate(data.get("components") or [])
        ]
        flow_lines = [f"{index + 1}. {item}" for index, item in enumerate(data.get("flow") or [])]
        return "\n\n".join(
            [
                data.get("summary", ""),
                "最小架构：\n" + "\n".join(component_lines),
                "执行流：\n" + "\n".join(flow_lines),
                "落地建议：\n" + data.get("implementation_hint", ""),
            ]
        )

    def _handle_langgraph(self, text: str) -> Dict[str, Any]:
        topic = text.strip()
        intent = self._classify_general_intent(topic)
        model_answer = self._call_model_for_general_answer(topic, intent)
        draft = model_answer or "模型服务未配置或调用失败，当前无法生成开放域回答。"
        corrections = self._review_general_answer(draft, intent)
        return {
            "draft": draft,
            "corrections": corrections,
            "model_used": bool(model_answer),
            "model_name": self.model_name if model_answer else "template_fallback",
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
                    "output_summary": ("model:" if model_answer else "template:") + draft[:120],
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
        if any(item in lowered for item in ["天气", "温度", "下雨", "晴天", "weather"]):
            return "weather"
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
                    "在这个项目里，下一步应该把 Agent 执行链路继续收敛：让 Planner 产出结构化步骤，Tool Registry 支持写补丁和跑测试，再把 trace 展示给前端而不是混进回答正文。",
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
        if intent == "weather":
            return (
                "当前 Agent 任务工作台还没有接入实时天气工具，所以不能直接确认广州此刻的天气。"
                "可以补充天气 API 工具后，让 Router 将天气类问题转到 weather 工具并返回温度、降雨、风力和更新时间。"
            )
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

    def _new_state(self, request: AgentChatRequest) -> Dict[str, str]:
        return {
            "run_id": f"run_{uuid.uuid4().hex}",
            "trace_id": f"trace_{uuid.uuid4().hex}",
            "session_id": request.session_id or f"session_{uuid.uuid4().hex}",
        }

    def _step_id(self) -> str:
        return f"step_{uuid.uuid4().hex}"

    def _tool_name(self, route: str) -> str:
        return {
            "leetcode_coach": "leetcode_coach",
            "java_stacktrace": "java_stacktrace_analyzer",
            "nl_to_sql": "nl_to_sql_generator",
            "agent_architecture": "agent_architecture_planner",
            "langgraph": "general_workflow",
        }.get(route, "general_workflow")

    def _structured(
            self,
            state: Dict[str, str],
            decision: RouteDecision,
            plan: List[Dict[str, Any]],
            steps: List[AgentChatStep],
            tool_calls: List[AgentChatToolCall],
            extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        structured = {
            "run_id": state["run_id"],
            "trace_id": state["trace_id"],
            "session_id": state["session_id"],
            "route_reason": decision["reason"],
            "route_confidence": decision["confidence"],
            "missing_context": decision["missing_context"],
            "plan": plan,
            "trace": [self._dump_model(step) for step in steps],
            "steps": [self._dump_model(step) for step in steps],
            "tool_calls": [self._dump_model(call) for call in tool_calls],
        }
        if extra:
            structured.update(extra)
        return structured

    def _missing_context_answer(self, decision: RouteDecision) -> str:
        if "schema" in decision["missing_context"]:
            return (
                "生成 SQL 前需要明确可用表结构。请补充 `context.schema`，或在消息里提供 `CREATE TABLE` / 表字段说明。"
                "在缺少 schema 的情况下，我不会直接编造表名和字段。"
            )
        return "还缺少必要上下文，请补充后继续。"

    def _deepest_caused_by(self, text: str) -> str:
        matches = re.findall(r"Caused by:\s*([^\n\r]+)", text, flags=re.IGNORECASE)
        return matches[-1].strip() if matches else ""

    def _evaluate_answer(self, answer: str, status: str) -> Dict[str, Any]:
        if status != "success":
            return {"summary": "failed", "answer_score": 0, "safety_score": 0}
        answer_score = 1 if answer.strip() else 0
        safety_score = 0 if "rm -rf" in answer.lower() else 1
        return {
            "summary": f"answer_score={answer_score}; safety_score={safety_score}",
            "answer_score": answer_score,
            "safety_score": safety_score,
        }

    def _output_summary(self, structured: Dict[str, Any], answer: str) -> str:
        if structured.get("error"):
            return str(structured["error"])[:160]
        if structured.get("summary"):
            return str(structured["summary"])[:160]
        return answer.replace("\n", " ")[:160]

    def _elapsed_ms(self, started: float) -> int:
        return int((time.perf_counter() - started) * 1000)

    def _answer_chunks(self, answer: str) -> Iterable[str]:
        chunk_size = 48
        for index in range(0, len(answer), chunk_size):
            yield answer[index:index + chunk_size]

    def _event(self, event: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return {"event": event, "data": data}

    def _error_payload(self, error: AgentChatError, state: Dict[str, str]) -> Dict[str, Any]:
        return {
            "error_code": error.error_code,
            "message": str(error),
            "retryable": error.retryable,
            "trace_id": state["trace_id"],
            "run_id": state["run_id"],
            "session_id": state["session_id"],
        }

    def _dump_model(self, model: Any) -> Dict[str, Any]:
        if hasattr(model, "model_dump"):
            return model.model_dump()
        if hasattr(model, "dict"):
            return model.dict()
        return dict(model)

    def _call_model_for_general_answer(self, question: str, intent: str) -> str:
        if not self.openai_api_key:
            return ""
        try:
            client = self._get_model_client()
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是 Tool Hub 的 Agent 任务工作台助手。"
                            "请用中文直接回答用户问题，保持准确、简洁、可执行。"
                            "如果问题需要实时数据而当前上下文没有工具结果，请明确说明没有实时数据来源，"
                            "不要编造当前天气、价格、新闻或时间敏感结论。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"意图：{intent}\n问题：{question}",
                    },
                ],
                temperature=0.2,
                max_tokens=700,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception:
            return ""

    def _route_with_model(self, text: str, context: Dict[str, Any]) -> Optional[RouteDecision]:
        if not self.openai_api_key:
            return None
        try:
            client = self._get_model_client()
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是 Agent skill 路由器。判断用户请求是否需要调用本地 skill。"
                            "可选 route: leetcode_coach, java_stacktrace, nl_to_sql, agent_architecture, langgraph。"
                            "只有算法题辅导、Java异常堆栈、自然语言转SQL、Agent架构设计明确需要本地 skill；"
                            "普通知识问答、地点、概念解释、闲聊、写作和不需要工具的问题使用 langgraph。"
                            "SQL 缺少表结构时 missing_context 必须包含 schema。"
                            "只输出 JSON，不要输出解释文字。格式："
                            "{\"route\":\"langgraph\",\"confidence\":0.8,\"missing_context\":[],\"reason\":\"...\"}"
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps({"message": text, "context": context}, ensure_ascii=False),
                    },
                ],
                temperature=0,
                max_tokens=220,
            )
            payload = self._parse_json_object(response.choices[0].message.content or "")
            route = str(payload.get("route") or "langgraph")
            if route not in self.ROUTE_TITLES:
                route = "langgraph"
            missing_context = payload.get("missing_context") or []
            if not isinstance(missing_context, list):
                missing_context = []
            for item in self._missing_context(route, text, context):
                if item not in missing_context:
                    missing_context.append(item)
            return {
                "route": route,  # type: ignore[typeddict-item]
                "reason": str(payload.get("reason") or "Model selected route."),
                "confidence": float(payload.get("confidence") or 0.7),
                "missing_context": [str(item) for item in missing_context],
            }
        except Exception:
            return None

    def _parse_json_object(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                return {}
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}

    def _get_model_client(self):
        if self._model_client is None:
            from openai import OpenAI

            kwargs = {"api_key": self.openai_api_key}
            if self.openai_api_base:
                kwargs["base_url"] = self.openai_api_base
            self._model_client = OpenAI(**kwargs)
        return self._model_client

    def _numbered(self, values: List[Any]) -> str:
        if not values:
            return "1. 无"
        return "\n".join(f"{index + 1}. {value}" for index, value in enumerate(values))
