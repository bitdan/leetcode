//给你一个字符串 s，找到 s 中最长的 回文 子串。 
//
// 
//
// 示例 1： 
//
// 
//输入：s = "babad"
//输出："bab"
//解释："aba" 同样是符合题意的答案。
// 
//
// 示例 2： 
//
// 
//输入：s = "cbbd"
//输出："bb"
// 
//
// 
//
// 提示： 
//
// 
// 1 <= s.length <= 1000 
// s 仅由数字和英文字母组成 
// 
//
// Related Topics 双指针 字符串 动态规划 👍 7902 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class LongestPalindromicSubstring {
    public static void main(String[] args) {
        Solution solution = new LongestPalindromicSubstring().new Solution();
        log.info("{}", solution.longestPalindrome("babad"));
    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public String longestPalindrome(String s) {
            int n = s.length();
            if (n < 2) {
                return s;
            }
            boolean[][] dp = new boolean[n][n];
            int maxLen = 1;
            int begin = 0;
            for (int i = 0; i < n; i++) {
                dp[i][i] = true;
            }

            for (int len = 2; len <= n; len++) {
                for (int i = 0; i < n; i++) {
                    int j = len + i - 1;
                    if (j >= n) {
                        break;
                    }
                    if (s.charAt(i) != s.charAt(j)) {
                        dp[i][j] = false;
                    } else {
                        if (j - i < 3) {
                            dp[i][j] = true;
                        }else {
                            dp[i][j] = dp[i + 1][j - 1];
                        }
                    }
                    if(dp[i][j]&&len>maxLen){
                        maxLen = len;
                        begin = i;
                    }
                }
            }
            return s.substring(begin,begin+maxLen);
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
