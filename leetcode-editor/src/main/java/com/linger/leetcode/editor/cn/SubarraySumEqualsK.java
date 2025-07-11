//给你一个整数数组 nums 和一个整数 k ，请你统计并返回 该数组中和为 k 的子数组的个数 。 
//
// 子数组是数组中元素的连续非空序列。 
//
// 
//
// 示例 1： 
//
// 
//输入：nums = [1,1,1], k = 2
//输出：2
// 
//
// 示例 2： 
//
// 
//输入：nums = [1,2,3], k = 3
//输出：2
// 
//
// 
//
// 提示： 
//
// 
// 1 <= nums.length <= 2 * 10⁴ 
// -1000 <= nums[i] <= 1000 
// -10⁷ <= k <= 10⁷ 
// 
//
// Related Topics 数组 哈希表 前缀和 👍 2809 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

import java.util.HashMap;

@Slf4j
public class SubarraySumEqualsK {
    public static void main(String[] args) {
        Solution solution = new SubarraySumEqualsK().new Solution();
        log.info("{}", solution.subarraySum(new int[]{1, 1, 1}, 2));
    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public int subarraySum(int[] nums, int k) {
            HashMap<Integer, Integer> map = new HashMap<>();
            map.put(0, 1); // 初始化
            int count = 0;
            int preifxSum = 0;
            for (int num : nums) {
                preifxSum += num;
                // // 如果存在prefixSum - k的前缀和，则增加计数
                if (map.containsKey(preifxSum - k)) {
                    count += map.get(preifxSum - k);
                }
                // 更新当前前缀和的出现次数
                map.put(preifxSum, map.getOrDefault(preifxSum, 0) + 1);
            }
            return count;
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
