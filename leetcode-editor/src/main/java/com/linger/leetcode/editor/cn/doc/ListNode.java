package com.linger.leetcode.editor.cn.doc;

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

}
