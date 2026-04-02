//给定一个单链表 L 的头节点 head ，单链表 L 表示为： 
//
// 
//L0 → L1 → … → Ln - 1 → Ln
// 
//
// 请将其重新排列后变为： 
//
// 
//L0 → Ln → L1 → Ln - 1 → L2 → Ln - 2 → … 
//
// 不能只是单纯的改变节点内部的值，而是需要实际的进行节点交换。 
//
// 
//
// 示例 1： 
//
// 
//
// 
//输入：head = [1,2,3,4]
//输出：[1,4,2,3] 
//
// 示例 2： 
//
// 
//
// 
//输入：head = [1,2,3,4,5]
//输出：[1,5,2,4,3] 
//
// 
//
// 提示： 
//
// 
// 链表的长度范围为 [1, 5 * 10⁴] 
// 1 <= node.val <= 1000 
// 
//
// Related Topics 栈 递归 链表 双指针 👍 1669 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class ReorderList {
    public static void main(String[] args) {

        Solution solution = new ReorderList().new Solution();
        ListNode listNode = ListNode.of(1, 2, 3, 4, 5);
        solution.reorderList(listNode);
        log.info("{}", listNode);

    }
    //leetcode submit region begin(Prohibit modification and deletion)

    class Solution {
        public void reorderList(ListNode head) {

            if (head == null || head.next == null) {
                return;
            }
            ListNode slow = head, fast = head.next;
            while (fast != null && fast.next != null) {
                slow = slow.next;
                fast = fast.next.next;
            }
            ListNode mid = slow.next;
            slow.next = null;
            ListNode reverse = reverse(mid);
            while (head != null && reverse != null) {
                ListNode temp1 = head.next;
                ListNode temp2 = reverse.next;
                head.next = reverse;
                reverse.next = temp1;
                head = temp1;
                reverse = temp2;
            }


        }

        public ListNode reverse(ListNode head) {
            ListNode pre = null;
            ListNode cur = head;
            while (cur != null) {
                ListNode next = cur.next;
                cur.next = pre;
                pre = cur;
                cur = next;
            }
            return pre;
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
