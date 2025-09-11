package com.linger.leetcode.editor.cn;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;

/**
 * @version 1.0
 * @description ListNode
 * @date 2025/9/11 09:44:46
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Slf4j
public class ListNode {
    public int val;
    public ListNode next;

    public ListNode(int x) {
        val = x;
        next = null;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        ListNode node = this;
        while (node != null) {
            sb.append(node.val);
            if (node.next != null) sb.append("->");
            node = node.next;
        }
        return sb.toString();
    }

    public static ListNode of(int... values) {
        if (values == null || values.length == 0) {
            return null;
        }
        ListNode head = new ListNode(values[0]);
        ListNode curr = head;
        for (int i = 1; i < values.length; i++) {
            curr.next = new ListNode(values[i]);
            curr = curr.next;
        }
        return head;
    }


    /**
     * 在尾部拼接链表，返回当前链表头
     */
    public ListNode append(ListNode other) {
        if (this == null) return other;
        ListNode curr = this;
        while (curr.next != null) {
            curr = curr.next;
        }
        curr.next = other;
        return this;
    }

    /**
     * 在头部拼接链表，返回新的头
     */
    public ListNode prepend(ListNode other) {
        if (other == null) return this;
        ListNode curr = other;
        while (curr.next != null) {
            curr = curr.next;
        }
        curr.next = this;
        return other;
    }


}
