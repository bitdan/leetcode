//给你两个整数数组 nums1 和 nums2，它们的长度分别为 m 和 n。数组 nums1 和 nums2 分别代表两个数各位上的数字。同时你也会得到一个
//整数 k。 
//
// 请你利用这两个数组中的数字创建一个长度为 k <= m + n 的最大数。同一数组中数字的相对顺序必须保持不变。 
//
// 返回代表答案的长度为 k 的数组。 
//
// 
//
// 示例 1： 
//
// 
//输入：nums1 = [3,4,6,5], nums2 = [9,1,2,5,8,3], k = 5
//输出：[9,8,6,5,3]
// 
//
// 示例 2： 
//
// 
//输入：nums1 = [6,7], nums2 = [6,0,4], k = 5
//输出：[6,7,6,0,4]
// 
//
// 示例 3： 
//
// 
//输入：nums1 = [3,9], nums2 = [8,9], k = 3
//输出：[9,8,9]
// 
//
// 
//
// 提示： 
//
// 
// m == nums1.length 
// n == nums2.length 
// 1 <= m, n <= 500 
// 0 <= nums1[i], nums2[i] <= 9 
// 1 <= k <= m + n 
// nums1 和 nums2 没有前导 0。 
// 
//
// Related Topics 栈 贪心 数组 双指针 单调栈 👍 630 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class CreateMaximumNumber {
    public static void main(String[] args) {
        Solution solution = new CreateMaximumNumber().new Solution();
        int[] nums1 = {3, 4, 6, 5};
        int[] nums2 = {9, 1, 2, 5, 8, 3};
        log.info("{}", solution.maxNumber(nums1, nums2, 5));
    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public int[] maxNumber(int[] nums1, int[] nums2, int k) {
            int m = nums1.length, n = nums2.length;
            int[] ans = new int[k];

            int start = Math.max(0, k - n);
            int end = Math.min(k, m);

            for (int i = start; i <= end; i++) {
                int[] part1 = maxSubsequence(nums1, i);
                int[] part2 = maxSubsequence(nums2, k - i);
                int[] candidate = merge(part1, part2);

                if (greater(candidate, 0, ans, 0)) {
                    ans = candidate;
                }
            }

            return ans;
        }

        // 从一个数组中选出长度为 k 的最大子序列
        private int[] maxSubsequence(int[] nums, int k) {
            int n = nums.length;
            int[] stack = new int[k];
            int top = -1;
            int remain = n - k;

            for (int num : nums) {
                while (top >= 0 && stack[top] < num && remain > 0) {
                    top--;
                    remain--;
                }
                if (top + 1 < k) {
                    stack[++top] = num;
                } else {
                    remain--;
                }
            }

            return stack;
        }

        // 合并两个序列，得到最大结果
        private int[] merge(int[] nums1, int[] nums2) {
            int x = nums1.length, y = nums2.length;
            int[] res = new int[x + y];
            int i = 0, j = 0, r = 0;

            while (i < x || j < y) {
                if (greater(nums1, i, nums2, j)) {
                    res[r++] = nums1[i++];
                } else {
                    res[r++] = nums2[j++];
                }
            }

            return res;
        }

        // 比较 nums1[i..] 是否大于 nums2[j..]
        private boolean greater(int[] nums1, int i, int[] nums2, int j) {
            while (i < nums1.length && j < nums2.length && nums1[i] == nums2[j]) {
                i++;
                j++;
            }
            if (j == nums2.length) return true;
            if (i == nums1.length) return false;
            return nums1[i] > nums2[j];
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
