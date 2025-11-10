//给你一个整数数组 nums 和一个整数 k ，请你返回其中出现频率前 k 高的元素。你可以按 任意顺序 返回答案。 
//
// 
//
// 示例 1： 
//
// 
// 输入：nums = [1,1,1,2,2,3], k = 2 
// 
//
// 输出：[1,2] 
//
// 示例 2： 
//
// 
// 输入：nums = [1], k = 1 
// 
//
// 输出：[1] 
//
// 示例 3： 
//
// 
// 输入：nums = [1,2,1,2,1,2,3,1,3,2], k = 2 
// 
//
// 输出：[1,2] 
//
// 
//
// 提示： 
//
// 
// 1 <= nums.length <= 10⁵ 
// k 的取值范围是 [1, 数组中不相同的元素的个数] 
// 题目数据保证答案唯一，换句话说，数组中前 k 个高频元素的集合是唯一的 
// 
//
// 
//
// 进阶：你所设计算法的时间复杂度 必须 优于 O(n log n) ，其中 n 是数组大小。 
//
// Related Topics 数组 哈希表 分治 桶排序 计数 快速选择 排序 堆（优先队列） 👍 2087 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

import java.util.HashMap;
import java.util.PriorityQueue;


@Slf4j
public class TopKFrequentElements {
    public static void main(String[] args) {
        Solution solution = new TopKFrequentElements().new Solution();
        int[] ints = {1, 1, 1, 2, 2, 3};
        log.info("{}", solution.topKFrequent(ints, 2));
    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public int[] topKFrequent(int[] nums, int k) {
            HashMap<Integer, Integer> hashMap = new HashMap<>();
            for (int num : nums) {
                hashMap.put(num, hashMap.getOrDefault(num, 0) + 1);
            }
            PriorityQueue<Object> queue = new PriorityQueue<>((a, b) -> hashMap.get(a) - hashMap.get(b));
            for (int key : hashMap.keySet()) {
                queue.add(key);
                if (queue.size() > k) {
                    queue.poll();
                }
            }
            int[] res = new int[k];
            for (int i = k - 1; i >= 0; i--) {
                res[i] = (int) queue.poll();
            }
            return res;
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
