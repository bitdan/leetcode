from pathlib import Path
import sys
from typing import Any, Dict


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from java_stacktrace_core import analyze_java_stacktrace


def analyze_stacktrace(stacktrace: str, context: str = "") -> Dict[str, Any]:
    """Skill entrypoint for Java stacktrace analysis."""
    return analyze_java_stacktrace(stacktrace=stacktrace, context=context)
