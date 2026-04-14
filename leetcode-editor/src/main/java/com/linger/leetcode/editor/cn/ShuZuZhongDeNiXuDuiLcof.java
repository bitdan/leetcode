//在股票交易中，如果前一天的股价高于后一天的股价，则可以认为存在一个「交易逆序对」。请设计一个程序，输入一段时间内的股票交易记录 record，返回其中存在的
//「交易逆序对」总数。 
//
// 
//
// 示例 1： 
//
// 
//输入：record = [9, 7, 5, 4, 6]
//输出：8
//解释：交易中的逆序对为 (9, 7), (9, 5), (9, 4), (9, 6), (7, 5), (7, 4), (7, 6), (5, 4)。
// 
//
// 
//
// 提示： 
//
// 0 <= record.length <= 50000 
//
// Related Topics 树状数组 线段树 数组 二分查找 分治 有序集合 归并排序 👍 1163 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class ShuZuZhongDeNiXuDuiLcof {
    public static void main(String[] args) {
        Solution solution = new ShuZuZhongDeNiXuDuiLcof().new Solution();
        int[] ints = {9, 7, 5, 4, 6};
        log.info("{}", solution.reversePairs(ints));
    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public int reversePairs(int[] record) {
            if (record == null || record.length < 2) {
                return 0;
            }
            int[] temp = new int[record.length];
            return mergeSort(record, 0, record.length - 1, temp);
        }

        private int mergeSort(int[] nums, int left, int right, int[] temp) {
            if (left >= right) {
                return 0;
            }

            int mid = left + (right - left) / 2;

            int leftCount = mergeSort(nums, left, mid, temp);
            int rightCount = mergeSort(nums, mid + 1, right, temp);

            // 小优化：如果左右本来就有序，就不用 merge 了
            if (nums[mid] <= nums[mid + 1]) {
                return leftCount + rightCount;
            }

            int mergeCount = merge(nums, left, mid, right, temp);
            return leftCount + rightCount + mergeCount;
        }

        private int merge(int[] nums, int left, int mid, int right, int[] temp) {
            for (int k = left; k <= right; k++) {
                temp[k] = nums[k];
            }

            int i = left;
            int j = mid + 1;
            int count = 0;

            for (int k = left; k <= right; k++) {
                if (i > mid) {
                    nums[k] = temp[j++];
                } else if (j > right) {
                    nums[k] = temp[i++];
                } else if (temp[i] <= temp[j]) {
                    nums[k] = temp[i++];
                } else {
                    nums[k] = temp[j++];
                    count += (mid - i + 1);
                }
            }

            return count;
        }

    }
//leetcode submit region end(Prohibit modification and deletion)

}
