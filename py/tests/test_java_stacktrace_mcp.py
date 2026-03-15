import sys
from pathlib import Path
import unittest


project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from mcp_server.java_stacktrace import analyze_java_stacktrace


class JavaStacktraceAnalyzerTest(unittest.TestCase):
    def test_null_pointer_analysis(self):
        stacktrace = """
java.lang.NullPointerException: Cannot invoke "com.example.demo.service.UserService.getUserById(java.lang.Long)" because "this.userService" is null
    at com.example.demo.controller.UserController.getUser(UserController.java:32)
    at org.springframework.web.method.support.InvocableHandlerMethod.doInvoke(InvocableHandlerMethod.java:205)
"""
        result = analyze_java_stacktrace(stacktrace, context="Spring MVC request")

        self.assertEqual("application_logic", result["category"])
        self.assertIn("NullPointerException", result["root_cause"])
        self.assertTrue(any("UserController.getUser" in item for item in result["evidence"]))
        self.assertTrue(any("constructor injection" in item.lower() for item in result["likely_fixes"]))


if __name__ == "__main__":
    unittest.main()
