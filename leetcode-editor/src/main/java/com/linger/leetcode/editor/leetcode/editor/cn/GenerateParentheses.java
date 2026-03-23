//数字 n 代表生成括号的对数，请你设计一个函数，用于能够生成所有可能的并且 有效的 括号组合。 
//
// 
//
// 示例 1： 
//
// 
//输入：n = 3
//输出：["((()))","(()())","(())()","()(())","()()()"]
// 
//
// 示例 2： 
//
// 
//输入：n = 1
//输出：["()"]
// 
//
// 
//
// 提示： 
//
// 
// 1 <= n <= 8 
// 
//
// Related Topics 字符串 动态规划 回溯 👍 4053 👎 0


package com.linger.leetcode.editor.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.List;

@Slf4j
public class GenerateParentheses {
    public static void main(String[] args) {
        Solution solution = new GenerateParentheses().new Solution();
        log.info("{}", solution.generateParenthesis(4));
    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public List<String> generateParenthesis(int n) {
            ArrayList<String> res = new ArrayList<>();
            StringBuilder stringBuilder = new StringBuilder();
            backtrack(res, stringBuilder, n, 0, 0);
            return res;
        }

        private void backtrack(List<String> ans, StringBuilder sb, int n, int left, int right) {
            if (left == n && right == n) {
                ans.add(sb.toString());
                return;
            }
            if (left < n) {
                sb.append('(');
                backtrack(ans, sb, n, left + 1, right);
                sb.deleteCharAt(sb.length() - 1);
            }
            if (right < left) {
                sb.append(')');
                backtrack(ans, sb, n, left, right + 1);
                sb.deleteCharAt(sb.length() - 1);
            }

        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
