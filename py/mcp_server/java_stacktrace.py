import importlib.util
from pathlib import Path
from typing import Dict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_STACKTRACE_SCRIPT = PROJECT_ROOT / "skills" / "java-stacktrace-analyzer" / "scripts" / "analyze_stacktrace.py"


def _load_skill_stacktrace_module():
    # 统一从 skill 目录加载执行入口，这样 MCP 只是 skill 的一层适配。
    spec = importlib.util.spec_from_file_location("skill_java_stacktrace_analyzer", SKILL_STACKTRACE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load java-stacktrace-analyzer script: {SKILL_STACKTRACE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_skill_stacktrace = _load_skill_stacktrace_module()


def analyze_java_stacktrace(stacktrace: str, context: str = "") -> Dict[str, object]:
    """Analyze a Java stack trace and return root cause, evidence, and likely fixes."""
    return _skill_stacktrace.analyze_stacktrace(stacktrace=stacktrace, context=context)
