from pathlib import Path
import sys
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PY_ROOT = PROJECT_ROOT / "py"

if str(PY_ROOT) not in sys.path:
    sys.path.append(str(PY_ROOT))

from mcp_server.java_stacktrace_core import analyze_java_stacktrace


def analyze_stacktrace(stacktrace: str, context: str = "") -> Dict[str, Any]:
    """Skill entrypoint for Java stacktrace analysis."""
    return analyze_java_stacktrace(stacktrace=stacktrace, context=context)
