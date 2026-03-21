import sys
from pathlib import Path
from typing import Any, Dict

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from workflow_core import run_workflow


def execute_workflow(topic: str) -> Dict[str, Any]:
    """Skill entrypoint for the general LangGraph workflow."""
    return run_workflow(topic)
