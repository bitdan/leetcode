import importlib.util
from pathlib import Path
from typing import Any, Dict

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


def run_leetcode_coach(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _skill_leetcode_coach.run_coach(**payload)
