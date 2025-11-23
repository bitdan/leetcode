//给你一个整数数组 nums ，请你找出数组中乘积最大的非空连续 子数组（该子数组中至少包含一个数字），并返回该子数组所对应的乘积。 
//
// 测试用例的答案是一个 32-位 整数。 
//
// 请注意，一个只包含一个元素的数组的乘积是这个元素的值。 
//
// 
//
// 示例 1: 
//
// 
//输入: nums = [2,3,-2,4]
//输出: 6
//解释: 子数组 [2,3] 有最大乘积 6。
// 
//
// 示例 2: 
//
// 
//输入: nums = [-2,0,-1]
//输出: 0
//解释: 结果不能为 2, 因为 [-2,-1] 不是子数组。 
//
// 
//
// 提示: 
//
// 
// 1 <= nums.length <= 2 * 10⁴ 
// -10 <= nums[i] <= 10 
// nums 的任何子数组的乘积都 保证 是一个 32-位 整数 
// 
//
// Related Topics 数组 动态规划 👍 2498 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class MaximumProductSubarray {
    public static void main(String[] args) {
        Solution solution = new MaximumProductSubarray().new Solution();
        log.info("{}", solution.maxProduct(new int[]{2, 3, -2, 4}));
    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public int maxProduct(int[] nums) {
            int max = nums[0];
            int min = nums[0];
            int res = nums[0];
            for (int i = 1; i < nums.length; i++) {
                int tmp = nums[i];
                int tmpMax = Math.max(tmp * max, Math.max(tmp * min, tmp));
                int tmpMin = Math.min(tmp * max, Math.min(tmp * min, tmp));
                max = tmpMax;
                min = tmpMin;
                res = Math.max(res, max);
            }
            return res;
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
