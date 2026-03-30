//给你一个链表的头节点 head ，旋转链表，将链表每个节点向右移动 k 个位置。 
//
// 
//
// 示例 1： 
// 
// 
//输入：head = [1,2,3,4,5], k = 2
//输出：[4,5,1,2,3]
// 
//
// 示例 2： 
// 
// 
//输入：head = [0,1,2], k = 4
//输出：[2,0,1]
// 
//
// 
//
// 提示： 
//
// 
// 链表中节点的数目在范围 [0, 500] 内 
// -100 <= Node.val <= 100 
// 0 <= k <= 2 * 10⁹ 
// 
//
// Related Topics 链表 双指针 👍 1183 👎 0


package com.linger.leetcode.editor.leetcode.editor.cn;

import com.linger.leetcode.editor.cn.ListNode;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class RotateList {
    public static void main(String[] args) {
        Solution solution = new RotateList().new Solution();
        ListNode head = ListNode.of(1, 2, 3, 4, 5);
        log.info("{}", solution.rotateRight(head, 2));
    }
    //leetcode submit region begin(Prohibit modification and deletion)

    class Solution {
        public ListNode rotateRight(ListNode head, int k) {
            if (head == null || head.next == null || k == 0) {
                return head;
            }
            int n = 1;
            ListNode tail = head;
            while (tail.next != null) {
                tail = tail.next;
                n++;
            }
            tail.next = head;
            int offset = n - k % n;
            ListNode newTail = head;
            for (int i = 0; i < offset - 1; i++) {
                newTail = newTail.next;
            }
            ListNode newHead = newTail.next;
            newTail.next = null;

            return newHead;
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
