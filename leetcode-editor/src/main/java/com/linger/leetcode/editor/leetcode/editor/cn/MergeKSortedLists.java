//给你一个链表数组，每个链表都已经按升序排列。 
//
// 请你将所有链表合并到一个升序链表中，返回合并后的链表。 
//
// 
//
// 示例 1： 
//
// 输入：lists = [[1,4,5],[1,3,4],[2,6]]
//输出：[1,1,2,3,4,4,5,6]
//解释：链表数组如下：
//[
//  1->4->5,
//  1->3->4,
//  2->6
//]
//将它们合并到一个有序链表中得到。
//1->1->2->3->4->4->5->6
// 
//
// 示例 2： 
//
// 输入：lists = []
//输出：[]
// 
//
// 示例 3： 
//
// 输入：lists = [[]]
//输出：[]
// 
//
// 
//
// 提示： 
//
// 
// k == lists.length 
// 0 <= k <= 10^4 
// 0 <= lists[i].length <= 500 
// -10^4 <= lists[i][j] <= 10^4 
// lists[i] 按 升序 排列 
// lists[i].length 的总和不超过 10^4 
// 
//
// Related Topics 链表 分治 堆（优先队列） 归并排序 👍 3183 👎 0


package com.linger.leetcode.editor.leetcode.editor.cn;

import com.linger.leetcode.editor.cn.ListNode;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class MergeKSortedLists {
    public static void main(String[] args) {
        Solution solution = new MergeKSortedLists().new Solution();
        log.info("{}", solution.mergeKLists(new ListNode[]{ListNode.of(1, 4, 5), ListNode.of(1, 3, 4), ListNode.of(2, 6)}));
    }
    //leetcode submit region begin(Prohibit modification and deletion)

    class Solution {
        public ListNode mergeKLists(ListNode[] lists) {

            if (lists == null || lists.length == 0){
                return null;
            }
            return merge(lists, 0, lists.length - 1);
        }

        private ListNode merge(ListNode[] lists, int left, int right) {
            if (left == right) {
                return lists[left];
            }
            int mid = left + (right - left) / 2;
            ListNode l1 = merge(lists, left, mid);
            ListNode l2 = merge(lists, mid + 1, right);
            return mergeTwoLists(l1, l2);
        }

        private ListNode mergeTwoLists(ListNode l1, ListNode l2) {
            ListNode dummy = new ListNode(-1);
            ListNode cur = dummy;
            while (l1 != null && l2 != null) {
                if (l1.val < l2.val) {
                    cur.next = l1;
                    l1 = l1.next;
                } else {
                    cur.next = l2;
                    l2 = l2.next;
                }
                cur = cur.next;
            }
            cur.next = l1 != null ? l1 : l2;
            return dummy.next;
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
