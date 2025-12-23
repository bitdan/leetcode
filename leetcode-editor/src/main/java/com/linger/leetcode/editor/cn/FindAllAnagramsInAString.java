//给定两个字符串 s 和 p，找到 s 中所有 p 的 异位词 的子串，返回这些子串的起始索引。不考虑答案输出的顺序。 
//
// 
//
// 示例 1: 
//
// 
//输入: s = "cbaebabacd", p = "abc"
//输出: [0,6]
//解释:
//起始索引等于 0 的子串是 "cba", 它是 "abc" 的异位词。
//起始索引等于 6 的子串是 "bac", 它是 "abc" 的异位词。
// 
//
// 示例 2: 
//
// 
//输入: s = "abab", p = "ab"
//输出: [0,1,2]
//解释:
//起始索引等于 0 的子串是 "ab", 它是 "ab" 的异位词。
//起始索引等于 1 的子串是 "ba", 它是 "ab" 的异位词。
//起始索引等于 2 的子串是 "ab", 它是 "ab" 的异位词。
// 
//
// 
//
// 提示: 
//
// 
// 1 <= s.length, p.length <= 3 * 10⁴ 
// s 和 p 仅包含小写字母 
// 
//
// Related Topics 哈希表 字符串 滑动窗口 👍 1701 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

@Slf4j
public class FindAllAnagramsInAString {
    public static void main(String[] args) {
        Solution solution = new FindAllAnagramsInAString().new Solution();
        log.info("{}", solution.findAnagrams("cbaebabacd", "abc"));

    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public List<Integer> findAnagrams(String s, String p) {
            ArrayList<Integer> list = new ArrayList<>();
            if (s.length() < p.length()) return list;
            int[] need = new int[26];
            int[] window = new int[26];
            for (int i = 0; i < p.length(); i++) {
                need[p.charAt(i) - 'a']++;
            }
            int left = 0;

            int right = 0;
            while (right < s.length()) {
                window[s.charAt(right) - 'a']++;
                right++;
                if (right - left == p.length()) {
                    if (Arrays.equals(need, window)) {
                        list.add(left);
                    }
                    window[s.charAt(left) - 'a']--;
                    left++;
                }
            }
            return list;
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
