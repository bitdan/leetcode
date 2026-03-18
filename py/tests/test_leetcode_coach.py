import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from api.main import app
from skill_adapters.leetcode_coach import run_leetcode_coach


class LeetCodeCoachApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_coach_endpoint_returns_heuristic_payload(self):
        payload = {
            "title": "Two Sum",
            "problem_statement": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
            "constraints": ["2 <= nums.length <= 10^4"],
            "examples": ["Input: nums = [2,7,11,15], target = 9 Output: [0,1]"],
            "code": "class Solution { public int[] twoSum(int[] nums, int target) { for (int i = 0; i < nums.length; i++) { } } }",
            "language": "java",
            "user_question": "我不知道怎么优化",
            "mode": "hint",
        }

        with patch("api.main.run_leetcode_coach") as mock_coach:
            mock_coach.return_value = {
                "understanding": "题目要求找到满足条件的两个下标。",
                "key_observations": ["先确认暴力解法，再思考如何用哈希表优化。"],
                "hint": "尝试边遍历边记录数字出现的位置。",
                "complexity_analysis": "暴力法 O(n^2)，哈希表法可降到 O(n)。",
                "review_findings": ["当前代码只有循环骨架，还没有真正判断逻辑。"],
                "next_step": "补上 target - nums[i] 的查找逻辑。",
                "similar_patterns": ["hash map counting"],
                "mode": "hint",
                "source": "heuristic",
            }
            response = self.client.post("/api/v1/leetcode/coach", json=payload)
        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertEqual("hint", data["mode"])
        self.assertIn("understanding", data)
        self.assertIn("complexity_analysis", data)
        self.assertTrue(data["review_findings"])
        self.assertIn(data["source"], {"heuristic", "llm"})


class LeetCodeCoachSkillTest(unittest.TestCase):
    def test_heuristic_response_has_learning_structure(self):
        with patch("skill_adapters.leetcode_coach._skill_leetcode_coach._service._can_use_llm", return_value=False):
            result = run_leetcode_coach(
                {
                    "title": "Valid Parentheses",
                    "problem_statement": "Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.",
                    "constraints": ["1 <= s.length <= 10^4"],
                    "examples": ["Input: s = \"()[]{}\" Output: true"],
                    "code": "class Solution { public boolean isValid(String s) { // TODO } }",
                    "language": "java",
                    "user_question": "提示我怎么想",
                    "mode": "teach",
                }
            )
        self.assertEqual("teach", result["mode"])
        self.assertTrue(result["hint"])
        self.assertTrue(result["key_observations"])
        self.assertTrue(result["similar_patterns"])
        self.assertEqual("heuristic", result["source"])


if __name__ == "__main__":
    unittest.main()
