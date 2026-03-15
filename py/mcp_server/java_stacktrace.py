import re
from typing import Dict, List, Optional


CAUSED_BY_PATTERN = re.compile(r"^\s*Caused by:\s+(.+)$", re.MULTILINE)
# 匹配典型 Java 堆栈帧，例如：
# at com.example.demo.controller.UserController.getUser(UserController.java:32)
USER_FRAME_PATTERN = re.compile(
    r"^\s*at\s+((?:[a-zA-Z_][\w$]*\.)+[A-Z][\w$]*\.[\w$<>]+)\(([^:()]+)(?::(\d+))?\)$",
    re.MULTILINE,
)
TOP_LEVEL_EXCEPTION_PATTERN = re.compile(r"^\s*([a-zA-Z_$][\w.$]+(?:: .+)?)$", re.MULTILINE)


def _extract_root_exception(stacktrace: str) -> str:
    # Java 异常通常最有价值的是最深层的 Caused by，而不是最外层包装异常。
    causes = CAUSED_BY_PATTERN.findall(stacktrace or "")
    if causes:
        return causes[-1].strip()

    for line in (stacktrace or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("java.") or stripped.startswith("javax.") or stripped.startswith("org."):
            return stripped
    match = TOP_LEVEL_EXCEPTION_PATTERN.search(stacktrace or "")
    return match.group(1).strip() if match else ""


def _extract_user_frame(stacktrace: str) -> Optional[Dict[str, str]]:
    for match in USER_FRAME_PATTERN.finditer(stacktrace or ""):
        method_path, file_name, line_no = match.groups()
        # 跳过 JDK / Spring 等框架栈帧，优先定位到用户自己的代码位置。
        if method_path.startswith(("org.springframework.", "java.", "javax.", "jakarta.", "sun.", "jdk.")):
            continue
        class_name, method_name = method_path.rsplit(".", 1)
        return {
            "class_name": class_name,
            "method_name": method_name,
            "file_name": file_name,
            "line_no": line_no or "",
            "frame": match.group(0).strip(),
        }
    return None


def _classify_exception(root_exception: str, stacktrace: str) -> str:
    # 这里做的是“轻量规则分类”，目的是给前端/调用方一个稳定的错误类型标签。
    text = f"{root_exception}\n{stacktrace}".lower()
    if any(token in text for token in ["beancreationexception", "unsatisfieddependencyexception", "nosuchbeandefinitionexception"]):
        return "spring_wiring"
    if any(token in text for token in ["configurationproperties", "could not resolve placeholder", "invalidconfigdata", "portinuseexception"]):
        return "configuration"
    if any(token in text for token in ["sqlexception", "jdbc", "cannotgetjdbcconnectionexception", "communications link failure", "sqlsyntaxerrorexception", "access denied for user"]):
        return "database"
    if any(token in text for token in ["classnotfoundexception", "noclassdeffounderror", "nosuchmethoderror", "nosuchfielderror"]):
        return "dependency"
    if any(token in text for token in ["mismatchedinputexception", "httpmessagenotreadableexception", "jsonparseexception"]):
        return "serialization"
    if any(token in text for token in ["compilation failure", "failed to execute goal", "could not resolve dependencies", "there are test failures"]):
        return "build"
    if any(token in text for token in ["outofmemoryerror", "stackoverflowerror", "rejectedexecutionexception"]):
        return "resource"
    return "application_logic"


def _build_fixes(category: str, root_exception: str, user_frame: Optional[Dict[str, str]]) -> List[str]:
    frame_ref = ""
    if user_frame:
        line_suffix = f":{user_frame['line_no']}" if user_frame.get("line_no") else ""
        frame_ref = f"{user_frame['file_name']}{line_suffix}"

    if "nullpointerexception" in root_exception.lower():
        fixes = [
            f"Check why the referenced dependency or variable is null at {frame_ref or 'the first user-code frame'}.",
            "If this is a Spring bean, prefer constructor injection and confirm the dependency class is annotated and scanned.",
            "If the value comes from request or database data, add input validation or null guards before dereferencing it.",
        ]
        return fixes

    # 这些建议不是自动修复，而是给调用方一个“先检查哪里”的排查入口。
    category_fixes = {
        "spring_wiring": [
            "Check the bean named in the exception chain and confirm it is annotated, scanned, and not excluded by profile or condition.",
            "Prefer constructor injection so missing dependencies fail at startup instead of later at runtime.",
        ],
        "configuration": [
            "Check the referenced property key, active profile, and environment variables.",
            "Verify the target config type matches the supplied value format.",
        ],
        "database": [
            "Check datasource URL, credentials, driver dependency, and network reachability first.",
            "If SQL is included, verify table names, column names, and dialect-specific syntax.",
        ],
        "dependency": [
            "Check dependency version conflicts and runtime classpath contents.",
            "For Maven builds, inspect `mvn dependency:tree` and align conflicting artifact versions.",
        ],
        "serialization": [
            "Check that the request or payload shape matches the target DTO fields and types.",
            "Verify enum values, array/object shapes, and Jackson annotations or constructors.",
        ],
        "build": [
            "Read the first compiler or plugin error before the summary footer and fix that one first.",
            "Check source compatibility, plugin configuration, and dependency resolution settings.",
        ],
        "resource": [
            "Check heap size, thread pool sizing, queue saturation, and recent load changes.",
            "If recursion is involved, inspect cyclic object graphs or uncontrolled recursive calls.",
        ],
        "application_logic": [
            "Inspect the first user-code frame and the values passed into that method.",
            "Add focused logging or a unit test around the failing path to confirm the bad state.",
        ],
    }
    return category_fixes.get(category, category_fixes["application_logic"])


def analyze_java_stacktrace(stacktrace: str, context: str = "") -> Dict[str, object]:
    """Analyze a Java stack trace and return root cause, evidence, and likely fixes."""
    normalized = (stacktrace or "").strip()
    if not normalized:
        raise ValueError("stacktrace is required")

    # 整体流程很简单：
    # 1. 找最深层异常
    # 2. 找第一条用户代码栈帧
    # 3. 归类
    # 4. 组装结构化结果
    root_exception = _extract_root_exception(normalized)
    user_frame = _extract_user_frame(normalized)
    category = _classify_exception(root_exception, normalized)

    evidence: List[str] = []
    if root_exception:
        evidence.append(f"Deepest actionable exception: {root_exception}")
    if user_frame:
        line_suffix = f":{user_frame['line_no']}" if user_frame.get("line_no") else ""
        evidence.append(
            f"First user-code frame: {user_frame['class_name']}.{user_frame['method_name']} ({user_frame['file_name']}{line_suffix})"
        )
    if context:
        evidence.append(f"Reported context: {context.strip()}")

    root_cause = root_exception or "Unable to isolate a root exception from the provided stack trace."
    if "nullpointerexception" in root_exception.lower() and user_frame:
        root_cause = (
            f"{root_exception}. The failing dereference happens in "
            f"{user_frame['class_name']}.{user_frame['method_name']}."
        )

    return {
        "category": category,
        "root_cause": root_cause,
        "evidence": evidence,
        "likely_fixes": _build_fixes(category, root_exception, user_frame),
        "missing_context": [] if user_frame else ["Relevant application code around the failing frame would improve confidence."],
    }
