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
        log.info("{}", solution.longestPalindrome("babbad"));
    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public String longestPalindrome(String s) {
            int start = 0, sublen = 0;
            for (int i = 0; i < s.length(); i++) {
                //bab
                int l = i, r = i;
                while (l >= 0 && r < s.length() && s.charAt(l) == s.charAt(r)) {
                    int len = r - l + 1;
                    if (len > sublen) {
                        start = l;
                        sublen = len;
                    }
                    l--;
                    r++;
                }

                //abba
                l = i;
                r = i + 1;
                while (l >= 0 && r < s.length() && s.charAt(l) == s.charAt(r)) {
                    int len = r - l + 1;
                    if (len > sublen) {
                        start = l;
                        sublen = len;
                    }
                    l--;
                    r++;
                }


            }
            return s.substring(start, start + sublen);
        }

    }
//leetcode submit region end(Prohibit modification and deletion)

}
