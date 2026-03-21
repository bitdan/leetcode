import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
PY_ROOT = REPO_ROOT / "py"
if str(PY_ROOT) not in sys.path:
    sys.path.append(str(PY_ROOT))

import config

logger = logging.getLogger(__name__)


class LeetCodeCoachRequest(BaseModel):
    title: str = Field(..., description="Problem title")
    problem_statement: str = Field(..., description="Full problem statement")
    constraints: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    code: str = Field(..., description="User submitted code")
    language: str = Field(default="java")
    user_question: str = Field(default="")
    mode: str = Field(default="hint")


class LeetCodeCoachResponse(BaseModel):
    understanding: str
    key_observations: List[str]
    hint: str
    complexity_analysis: str
    review_findings: List[str]
    next_step: str
    similar_patterns: List[str]
    mode: str
    source: str


class LeetCodeCoachService:
    def __init__(self, model_name: str = "gpt-4o-mini") -> None:
        self._model_name = model_name
        self._llm: Optional[ChatOpenAI] = None

    def coach(self, request: LeetCodeCoachRequest) -> LeetCodeCoachResponse:
        normalized_mode = request.mode.strip().lower() or "hint"
        if self._can_use_llm():
            try:
                payload = self._invoke_llm(request, normalized_mode)
                return LeetCodeCoachResponse(**payload, mode=normalized_mode, source="llm")
            except Exception:
                logger.exception("leetcode_coach LLM invoke failed, fallback to heuristic mode")

        payload = self._heuristic_response(request, normalized_mode)
        return LeetCodeCoachResponse(**payload, mode=normalized_mode, source="heuristic")

    def _can_use_llm(self) -> bool:
        return bool(config.OPENAI_API_KEY)

    def _get_llm(self) -> ChatOpenAI:
        if self._llm is None:
            self._llm = ChatOpenAI(
                temperature=0.2,
                model=self._model_name,
                openai_api_key=config.OPENAI_API_KEY,
                openai_api_base=config.OPENAI_API_BASE,
                request_timeout=60,
                max_retries=2,
            )
        return self._llm

    def _invoke_llm(self, request: LeetCodeCoachRequest, mode: str) -> Dict[str, Any]:
        constraints = "\n".join(f"- {item}" for item in request.constraints) or "- None provided"
        examples = "\n".join(f"- {item}" for item in request.examples) or "- None provided"

        prompt = f"""
你是一个 LeetCode 陪练教练。目标是帮助用户学会做题，不要默认直接给完整答案。

请基于以下输入输出 JSON，对用户的代码做教学式反馈。

要求：
1. 默认站在陪练角度，优先帮助理解题目和下一步改进。
2. 如果 mode=hint，不要直接给完整可提交代码。
3. 复杂度分析要明确提及时间复杂度和空间复杂度。
4. review_findings 要优先指出 bug、边界条件、复杂度风险、可读性问题。
5. similar_patterns 给 2 到 4 个相关题型或方法。
6. 输出必须是合法 JSON，不要附带 markdown。

输入：
title: {request.title}
mode: {mode}
language: {request.language}
user_question: {request.user_question or "None"}
problem_statement:
{request.problem_statement}

constraints:
{constraints}

examples:
{examples}

user_code:
{request.code}

JSON schema:
{{
  "understanding": "string",
  "key_observations": ["string"],
  "hint": "string",
  "complexity_analysis": "string",
  "review_findings": ["string"],
  "next_step": "string",
  "similar_patterns": ["string"]
}}
""".strip()

        content = self._get_llm().invoke(prompt).content
        if not isinstance(content, str):
            raise ValueError("Unexpected LLM content type")
        parsed = json.loads(self._extract_json(content))
        return self._normalize_payload(parsed)

    def _extract_json(self, content: str) -> str:
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3:
                text = "\n".join(lines[1:-1]).strip()
        return text

    def _normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "understanding": str(payload.get("understanding", "")).strip(),
            "key_observations": self._coerce_list(payload.get("key_observations")),
            "hint": str(payload.get("hint", "")).strip(),
            "complexity_analysis": str(payload.get("complexity_analysis", "")).strip(),
            "review_findings": self._coerce_list(payload.get("review_findings")),
            "next_step": str(payload.get("next_step", "")).strip(),
            "similar_patterns": self._coerce_list(payload.get("similar_patterns")),
        }

    def _coerce_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if value is None:
            return []
        text = str(value).strip()
        return [text] if text else []

    def _heuristic_response(self, request: LeetCodeCoachRequest, mode: str) -> Dict[str, Any]:
        code = request.code or ""
        title = request.title.strip() or "This problem"
        lower_code = code.lower()

        key_observations = [
            f"{title} should be reduced to input, output, constraints, and the exact condition you need to maintain.",
            "Before changing code, confirm the brute-force idea and why it may or may not fit the constraints.",
        ]

        if request.constraints:
            key_observations.append(f"Constraint focus: {request.constraints[0]}")

        review_findings = []
        if not code.strip():
            review_findings.append(
                "No code was provided, so the main next step is to write a minimal working brute-force version.")
        if "todo" in lower_code:
            review_findings.append("The code still contains TODO markers, which suggests the core logic is incomplete.")
        if "while" in lower_code and "for" in lower_code:
            review_findings.append(
                "Nested iteration patterns may be acceptable, but you should verify whether they violate the intended complexity target.")
        if "null" in lower_code or "none" in lower_code:
            review_findings.append("Check null or empty-input handling explicitly instead of assuming valid data.")
        if "return" not in lower_code:
            review_findings.append("The submitted code does not appear to have a clear return path yet.")
        if not review_findings:
            review_findings.append(
                "Verify edge cases such as empty input, single-element input, repeated values, and maximum constraint size.")

        hint_parts = [
            "Start by restating what state or invariant you need to maintain while scanning the input.",
            "Then test that idea on the smallest non-trivial example and one boundary case.",
        ]
        if mode == "review":
            hint_parts.insert(0,
                              "Read the current code from top to bottom and explain what each branch is trying to guarantee.")
        elif mode == "teach":
            hint_parts.insert(0,
                              "Focus on why the standard pattern for this problem family works, not just what to code.")
        elif mode == "mock":
            hint_parts.insert(0,
                              "Pretend you are in an interview and justify each data structure choice before writing code.")

        next_step = (
            "Write down the target complexity, walk through one example by hand, then revise only the part of the code "
            "that breaks the invariant or misses an edge case."
        )

        return {
            "understanding": (
                f"{title} needs a clear mapping from the problem statement to an algorithmic pattern. "
                "You should first identify the input shape, output expectation, and the constraint that rules out weaker approaches."
            ),
            "key_observations": key_observations[:3],
            "hint": " ".join(hint_parts),
            "complexity_analysis": self._build_complexity_analysis(request),
            "review_findings": review_findings[:4],
            "next_step": next_step,
            "similar_patterns": self._infer_patterns(request),
        }

    def _build_complexity_analysis(self, request: LeetCodeCoachRequest) -> str:
        code = request.code.lower()
        if "for" in code and "while" in code:
            return (
                "The current code likely mixes multiple passes or nested control flow. "
                "Estimate whether it behaves closer to O(n^2) in the worst case, and check whether that matches the constraints. "
                "Space usage appears to depend on auxiliary structures in the code and should be reviewed explicitly."
            )
        if "for" in code:
            return (
                "The current code looks like a single-pass or multi-pass iteration approach. "
                "Validate whether the time complexity is O(n) or O(n log n) depending on sorting or lookup structures, "
                "and state the extra space introduced by arrays, maps, stacks, or recursion."
            )
        return (
            "The complexity is not obvious from the current submission. "
            "Write down the dominant loop, recursion depth, or data-structure operations so you can express time and space complexity clearly."
        )

    def _infer_patterns(self, request: LeetCodeCoachRequest) -> List[str]:
        haystack = " ".join(
            [
                request.title.lower(),
                request.problem_statement.lower(),
                " ".join(item.lower() for item in request.constraints),
            ]
        )
        patterns = []
        pattern_keywords = [
            ("sliding window", ["substring", "subarray", "window"]),
            ("two pointers", ["sorted", "pair", "palindrome", "two pointers"]),
            ("binary search", ["sorted", "search", "monotonic"]),
            ("dynamic programming", ["maximum", "minimum", "count ways", "subsequence"]),
            ("graph traversal", ["graph", "island", "matrix", "bfs", "dfs"]),
            ("monotonic stack", ["next greater", "histogram", "stack"]),
            ("hash map counting", ["duplicate", "frequency", "anagram", "count"]),
        ]
        for name, keywords in pattern_keywords:
            if any(keyword in haystack for keyword in keywords):
                patterns.append(name)
        if not patterns:
            patterns = ["brute force to optimized refinement", "edge-case driven debugging"]
        return patterns[:4]
