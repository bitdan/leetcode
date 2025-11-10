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
            PriorityQueue<Integer> minHeap = new PriorityQueue<>();
            for (int num : nums) {
                minHeap.offer(num);
                if (minHeap.size()>k){
                    minHeap.poll();
                }
            }
            return minHeap.peek();
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
