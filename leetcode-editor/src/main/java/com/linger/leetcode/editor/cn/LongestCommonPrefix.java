//编写一个函数来查找字符串数组中的最长公共前缀。 
//
// 如果不存在公共前缀，返回空字符串 ""。 
//
// 
//
// 示例 1： 
//
// 
//输入：strs = ["flower","flow","flight"]
//输出："fl"
// 
//
// 示例 2： 
//
// 
//输入：strs = ["dog","racecar","car"]
//输出：""
//解释：输入不存在公共前缀。 
//
// 
//
// 提示： 
//
// 
// 1 <= strs.length <= 200 
// 0 <= strs[i].length <= 200 
// strs[i] 如果非空，则仅由小写英文字母组成 
// 
//
// Related Topics 字典树 数组 字符串 👍 3485 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class LongestCommonPrefix {
    public static void main(String[] args) {
        Solution solution = new LongestCommonPrefix().new Solution();
        log.info("{}", solution.longestCommonPrefix(new String[]{"dog","racecar","car"}));
    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public String longestCommonPrefix(String[] strs) {
            if (strs == null || strs.length == 0) return "";

            String first = strs[0];

            for (int i = 0; i < first.length(); i++) {
                char c = first.charAt(i);

                for (int j = 1; j < strs.length; j++) {
                    // 越界 or 不相等
                    if (i >= strs[j].length() || strs[j].charAt(i) != c) {
                        return first.substring(0, i);
                    }
                }
            }

            return first;
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
