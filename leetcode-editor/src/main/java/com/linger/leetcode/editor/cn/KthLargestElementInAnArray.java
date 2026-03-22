//给定整数数组 nums 和整数 k，请返回数组中第 k 个最大的元素。 
//
// 请注意，你需要找的是数组排序后的第 k 个最大的元素，而不是第 k 个不同的元素。 
//
// 你必须设计并实现时间复杂度为 O(n) 的算法解决此问题。 
//
// 
//
// 示例 1: 
//
// 
//输入: [3,2,1,5,6,4], k = 2
//输出: 5
// 
//
// 示例 2: 
//
// 
//输入: [3,2,3,1,2,4,5,5,6], k = 4
//输出: 4 
//
// 
//
// 提示： 
//
// 
// 1 <= k <= nums.length <= 10⁵ 
// -10⁴ <= nums[i] <= 10⁴ 
// 
//
// Related Topics 数组 分治 快速选择 排序 堆（优先队列） 👍 2848 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

import java.util.PriorityQueue;
import java.util.Random;

@Slf4j
public class KthLargestElementInAnArray {
    public static void main(String[] args) {
        Solution solution = new KthLargestElementInAnArray().new Solution();
        int[] ints = {3, 2, 1, 5, 6, 4};
        log.info("{}", solution.findKthLargest(ints, 2));

    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {

        public int findKthLargest(int[] nums, int k) {
            int target = nums.length - k;
            int left = 0;
            int right = nums.length - 1;
            while (left <= right) {
                int index = partition(nums, left, right);
                if (index == target) {
                    return nums[index];
                } else if (index > target) {
                    right = index - 1;
                } else if (index < target) {
                    left = index + 1;
                }
            }
            return -1;
        }

        private int partition(int[] nums, int left, int right) {
            int p = nums[right];
            int i = left;
            for (int j = left; j < right; j++) {
                if (nums[j] < p) {
                    swap(nums, i, j);
                    i++;
                }
            }
            swap(nums, i, right);
            return i;
        }

        private void swap(int[] nums, int i, int j) {
            int temp = nums[i];
            nums[i] = nums[j];
            nums[j] = temp;
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
