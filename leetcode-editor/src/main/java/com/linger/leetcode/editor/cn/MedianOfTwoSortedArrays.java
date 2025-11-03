//给定两个大小分别为 m 和 n 的正序（从小到大）数组 nums1 和 nums2。请你找出并返回这两个正序数组的 中位数 。 
//
// 算法的时间复杂度应该为 O(log (m+n)) 。 
//
// 
//
// 示例 1： 
//
// 
//输入：nums1 = [1,3], nums2 = [2]
//输出：2.00000
//解释：合并数组 = [1,2,3] ，中位数 2
// 
//
// 示例 2： 
//
// 
//输入：nums1 = [1,2], nums2 = [3,4]
//输出：2.50000
//解释：合并数组 = [1,2,3,4] ，中位数 (2 + 3) / 2 = 2.5
// 
//
// 
//
// 
//
// 提示： 
//
// 
// nums1.length == m 
// nums2.length == n 
// 0 <= m <= 1000 
// 0 <= n <= 1000 
// 1 <= m + n <= 2000 
// -10⁶ <= nums1[i], nums2[i] <= 10⁶ 
// 
//
// Related Topics 数组 二分查找 分治 👍 7741 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class MedianOfTwoSortedArrays {
    public static void main(String[] args) {
        Solution solution = new MedianOfTwoSortedArrays().new Solution();
        log.info("{}", solution.findMedianSortedArrays(new int[]{1, 3}, new int[]{2}));
    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public double findMedianSortedArrays(int[] nums1, int[] nums2) {
            // 保证 nums1 是较短的数组，减少二分搜索范围
            if (nums1.length > nums2.length) {
                return findMedianSortedArrays(nums2, nums1);
            }

            int m = nums1.length, n = nums2.length;
            int totalLeft = (m + n + 1) / 2;

            int left = 0, right = m; // 在 nums1 中二分

            while (left < right) {
                int i = (left + right + 1) / 2;
                int j = totalLeft - i;

                if (nums1[i - 1] > nums2[j]) {
                    // i 太大了，左移
                    right = i - 1;
                } else {
                    // i 太小，右移
                    left = i;
                }
            }

            int i = left;
            int j = totalLeft - i;

            // 边界处理（如果越界则取极值）
            int nums1LeftMax = (i == 0) ? Integer.MIN_VALUE : nums1[i - 1];
            int nums1RightMin = (i == m) ? Integer.MAX_VALUE : nums1[i];
            int nums2LeftMax = (j == 0) ? Integer.MIN_VALUE : nums2[j - 1];
            int nums2RightMin = (j == n) ? Integer.MAX_VALUE : nums2[j];

            if ((m + n) % 2 == 1) {
                return Math.max(nums1LeftMax, nums2LeftMax);
            } else {
                return (Math.max(nums1LeftMax, nums2LeftMax) +
                        Math.min(nums1RightMin, nums2RightMin)) / 2.0;
            }
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
