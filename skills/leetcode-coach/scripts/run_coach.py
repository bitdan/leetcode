import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from coach_core import LeetCodeCoachRequest, LeetCodeCoachService

_service = LeetCodeCoachService()


def run_coach(
        title: str,
        problem_statement: str,
        code: str,
        constraints: List[str] | None = None,
        examples: List[str] | None = None,
        language: str = "java",
        user_question: str = "",
        mode: str = "hint",
) -> Dict[str, Any]:
    """Skill entrypoint for LeetCode coaching."""
    request = LeetCodeCoachRequest(
        title=title,
        problem_statement=problem_statement,
        constraints=constraints or [],
        examples=examples or [],
        code=code,
        language=language,
        user_question=user_question,
        mode=mode,
    )
    return _service.coach(request).model_dump()
