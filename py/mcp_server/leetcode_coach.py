import importlib.util
from pathlib import Path
from typing import Any, Dict, List

from mcp_server.path_utils import find_repo_root

PROJECT_ROOT = find_repo_root(Path(__file__))
SKILL_COACH_SCRIPT = PROJECT_ROOT / "skills" / "leetcode-coach" / "scripts" / "run_coach.py"


def _load_skill_leetcode_coach_module():
    spec = importlib.util.spec_from_file_location("skill_leetcode_coach", SKILL_COACH_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load leetcode-coach script: {SKILL_COACH_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_skill_leetcode_coach = _load_skill_leetcode_coach_module()


def run_leetcode_coach(
        title: str,
        problem_statement: str,
        code: str,
        constraints: List[str] | None = None,
        examples: List[str] | None = None,
        language: str = "java",
        user_question: str = "",
        mode: str = "hint",
) -> Dict[str, Any]:
    """Run the leetcode coach skill through its stable script entrypoint."""
    return _skill_leetcode_coach.run_coach(
        title=title,
        problem_statement=problem_statement,
        code=code,
        constraints=constraints or [],
        examples=examples or [],
        language=language,
        user_question=user_question,
        mode=mode,
    )
