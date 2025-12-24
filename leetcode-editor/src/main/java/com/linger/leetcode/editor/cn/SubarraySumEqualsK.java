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
        log.info("{}", solution.subarraySum(new int[]{1, 2, 3}, 3));
    }

    /**
     * 初始化哈希表 ：prefixSumCount 用于存储前缀和及其出现次数，初始时前缀和为0出现1次
     * 遍历数组 ：计算当前前缀和 prefixSum
     * 查找目标前缀和 ：检查是否存在 prefixSum - k，如果存在则增加计数
     * 更新哈希表 ：将当前前缀和的出现次数存入哈希表
     */
    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public int subarraySum(int[] nums, int k) {
            HashMap<Integer, Integer> map = new HashMap<>();
            map.put(0, 1); // 初始化
            int res = 0;
            int sum = 0;
            // map 是每个数字的统计和, 减去k 就是剩余出现过得, 统计出现几次就行
            for (int i = 0; i < nums.length; i++) {
                sum += nums[i];
                // // 如果存在prefixSum - k的前缀和，则增加计数
                if (map.containsKey(sum - k)) {
                    res += map.get(sum - k);
                }
                map.put(sum, map.getOrDefault(sum, 0) + 1);
            }
            return res;
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
