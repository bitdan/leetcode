//给你一个字符串数组，请你将 字母异位词 组合在一起。可以按任意顺序返回结果列表。 
//
// 
//
// 示例 1: 
//
// 
// 输入: strs = ["eat", "tea", "tan", "ate", "nat", "bat"] 
// 
//
// 输出: [["bat"],["nat","tan"],["ate","eat","tea"]] 
//
// 解释： 
//
// 
// 在 strs 中没有字符串可以通过重新排列来形成 "bat"。 
// 字符串 "nat" 和 "tan" 是字母异位词，因为它们可以重新排列以形成彼此。 
// 字符串 "ate" ，"eat" 和 "tea" 是字母异位词，因为它们可以重新排列以形成彼此。 
// 
//
// 示例 2: 
//
// 
// 输入: strs = [""] 
// 
//
// 输出: [[""]] 
//
// 示例 3: 
//
// 
// 输入: strs = ["a"] 
// 
//
// 输出: [["a"]] 
//
// 
//
// 提示： 
//
// 
// 1 <= strs.length <= 10⁴ 
// 0 <= strs[i].length <= 100 
// strs[i] 仅包含小写字母 
// 
//
// Related Topics 数组 哈希表 字符串 排序 👍 2302 👎 0


package com.linger.leetcode;

import lombok.extern.slf4j.Slf4j;

import java.util.*;

@Slf4j
public class GroupAnagrams {
    public static void main(String[] args) {
        Solution solution = new GroupAnagrams().new Solution();
        String[] strings = {"eat", "tea", "tan", "ate", "nat", "bat"};
        List<List<String>> lists = solution.groupAnagrams(strings);
        log.info("lists is : {}", lists);
    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public List<List<String>> groupAnagrams(String[] strs) {
            Map<String, List<String>> map = new HashMap<>();
            for (String str : strs) {
                char[] charArray = str.toCharArray();
                Arrays.sort(charArray);
                String newStr = new String(charArray);
                map.computeIfAbsent(newStr, k -> new ArrayList<>()).add(str);
            }
            return new ArrayList<>(map.values());
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
