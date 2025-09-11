//给你一个单链表的头节点 head ，请你判断该链表是否为回文链表。如果是，返回 true ；否则，返回 false 。 
//
// 
//
// 示例 1： 
// 
// 
//输入：head = [1,2,2,1]
//输出：true
// 
//
// 示例 2： 
// 
// 
//输入：head = [1,2]
//输出：false
// 
//
// 
//
// 提示： 
//
// 
// 链表中节点数目在范围[1, 10⁵] 内 
// 0 <= Node.val <= 9 
// 
//
// 
//
// 进阶：你能否用 O(n) 时间复杂度和 O(1) 空间复杂度解决此题？ 
//
// Related Topics 栈 递归 链表 双指针 👍 2114 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class PalindromeLinkedList {
    public static void main(String[] args) {
        Solution solution = new PalindromeLinkedList().new Solution();
        ListNode node = ListNode.of(1, 2, 2, 1);
        log.info("{}", solution.isPalindrome(node));
    }
    //leetcode submit region begin(Prohibit modification and deletion)



    class Solution {
        public boolean isPalindrome(ListNode head) {
            if (head == null || head.next == null) return true;
            ListNode slow = head;
            ListNode fast = head;
            while (fast.next != null && fast.next.next != null) {
                slow = slow.next;
                fast = fast.next.next;
            }
            if (fast != null) {
                slow = slow.next;
            }
            ListNode reverse = reverseList(slow);
            ListNode p1 = head;
            ListNode p2 = reverse;
            while (p2 != null) {
                if (p1.val != p2.val) {
                    return false;
                }
                p1 = p1.next;
                p2 = p2.next;
            }
            return true;
        }


        public ListNode reverseList(ListNode head) {
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
