import importlib.util
from pathlib import Path
from typing import Any, Dict

from mcp_server.path_utils import find_repo_root

PROJECT_ROOT = find_repo_root(Path(__file__))
SKILL_WORKFLOW_SCRIPT = PROJECT_ROOT / "skills" / "langgraph-workflow" / "scripts" / "run_workflow.py"


def _load_skill_workflow_module():
    spec = importlib.util.spec_from_file_location("skill_langgraph_workflow", SKILL_WORKFLOW_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load langgraph-workflow script: {SKILL_WORKFLOW_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_skill_workflow = _load_skill_workflow_module()


def execute_langgraph_workflow(topic: str) -> Dict[str, Any]:
    """Run the general workflow through the skill entrypoint."""
    return _skill_workflow.execute_workflow(topic=topic)
