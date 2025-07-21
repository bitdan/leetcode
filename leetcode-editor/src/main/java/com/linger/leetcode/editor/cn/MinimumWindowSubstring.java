//给你一个字符串 s 、一个字符串 t 。返回 s 中涵盖 t 所有字符的最小子串。如果 s 中不存在涵盖 t 所有字符的子串，则返回空字符串 "" 。 
//
// 
//
// 注意： 
//
// 
// 对于 t 中重复字符，我们寻找的子字符串中该字符数量必须不少于 t 中该字符数量。 
// 如果 s 中存在这样的子串，我们保证它是唯一的答案。 
// 
//
// 
//
// 示例 1： 
//
// 
//输入：s = "ADOBECODEBANC", t = "ABC"
//输出："BANC"
//解释：最小覆盖子串 "BANC" 包含来自字符串 t 的 'A'、'B' 和 'C'。
// 
//
// 示例 2： 
//
// 
//输入：s = "a", t = "a"
//输出："a"
//解释：整个字符串 s 是最小覆盖子串。
// 
//
// 示例 3: 
//
// 
//输入: s = "a", t = "aa"
//输出: ""
//解释: t 中两个字符 'a' 均应包含在 s 的子串中，
//因此没有符合条件的子字符串，返回空字符串。 
//
// 
//
// 提示： 
//
// 
// m == s.length 
// n == t.length 
// 1 <= m, n <= 10⁵ 
// s 和 t 由英文字母组成 
// 
//
// 
//进阶：你能设计一个在 
//o(m+n) 时间内解决此问题的算法吗？
//
// Related Topics 哈希表 字符串 滑动窗口 👍 3314 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

import java.util.HashMap;
import java.util.Map;

@Slf4j
public class MinimumWindowSubstring {
    public static void main(String[] args) {
        Solution solution = new MinimumWindowSubstring().new Solution();
        String s = "ADOBECODEBANC";
        String t = "ABC";
        log.info("{}", solution.minWindow(s, t));
    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public String minWindow(String s, String t) {
            if (s.length() < t.length()) return "";

            // 1. 统计 t 中的字符频率
            Map<Character, Integer> targetMap = new HashMap<>();
            for (char c : t.toCharArray()) {
                targetMap.put(c, targetMap.getOrDefault(c, 0) + 1);
            }

            // 2. 滑动窗口：左指针、右指针
            int left = 0, right = 0;
            // 记录当前窗口中字符的频率
            Map<Character, Integer> windowMap = new HashMap<>();
            // 有效匹配的字符数
            int formed = 0;
            int required = targetMap.size();

            // 结果：最小窗口的长度、左边界、右边界
            int minLen = Integer.MAX_VALUE;
            int minLeft = 0, minRight = 0;

            while (right < s.length()) {
                char c = s.charAt(right);
                windowMap.put(c, windowMap.getOrDefault(c, 0) + 1);

                // 如果当前字符频率达到了要求，formed++
                if (targetMap.containsKey(c) &&
                        windowMap.get(c).intValue() == targetMap.get(c).intValue()) {
                    formed++;
                }

                // 收缩窗口直到不满足条件
                while (left <= right && formed == required) {
                    // 更新最小窗口
                    if (right - left + 1 < minLen) {
                        minLen = right - left + 1;
                        minLeft = left;
                        minRight = right;
                    }

                    char lc = s.charAt(left);
                    windowMap.put(lc, windowMap.get(lc) - 1);
                    if (targetMap.containsKey(lc) &&
                            windowMap.get(lc).intValue() < targetMap.get(lc).intValue()) {
                        formed--;
                    }
                    left++;
                }

                // 扩展窗口
                right++;
            }

            return minLen == Integer.MAX_VALUE ? "" : s.substring(minLeft, minRight + 1);
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
