package com.linger.leetcode.editor.cn;

import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.Set;

/**
 * @version 1.0
 * @description ListNode
 * @date 2025/9/11 09:44:46
 */
@NoArgsConstructor
@AllArgsConstructor
@Slf4j
public class ListNode {
    public int val;
    public ListNode next;
    public ListNode random;

    public ListNode(int x) {
        val = x;
        next = null;
        random = null;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        ListNode node = this;
        Set<ListNode> visited = Collections.newSetFromMap(new IdentityHashMap<>());
        while (node != null) {
            if (visited.contains(node)) {
                sb.append(node.val).append("->(cycle to ").append(node.val).append(")");
                break;
            }
            visited.add(node);
            sb.append(node.val);
            if (node.next != null) sb.append("->");
            node = node.next;
        }
        return sb.toString();
    }


    /**
     * 创建链表
     *
     * @param values
     * @return
     */
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

    public static ListNode ofWithRandom(Integer[][] nodes) {
        if (nodes == null || nodes.length == 0) {
            return null;
        }

        // 1. 先创建所有节点（只设置 val 和 next）
        ListNode[] list = new ListNode[nodes.length];
        for (int i = 0; i < nodes.length; i++) {
            list[i] = new ListNode(nodes[i][0]);
        }
        for (int i = 0; i < nodes.length - 1; i++) {
            list[i].next = list[i + 1];
        }

        // 2. 再设置 random
        for (int i = 0; i < nodes.length; i++) {
            Integer randomIndex = nodes[i][1];
            if (randomIndex != null) {
                list[i].random = list[randomIndex];
            }
        }

        return list[0];
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


    /**
     * 根据下标 pos 构造环
     * pos = -1 表示无环
     * pos >= 0 表示尾结点连回第 pos 个节点（0-based）
     */
    public ListNode withCycle(int pos) {
        if (pos < 0) return this;

        ListNode tail = this;
        ListNode cycleEntry = null;
        int index = 0;
        ListNode curr = this;
        while (curr != null) {
            if (index == pos) {
                cycleEntry = curr;
            }
            if (curr.next == null) {
                tail = curr;
            }
            curr = curr.next;
            index++;
        }
        if (cycleEntry != null) {
            tail.next = cycleEntry;
        }
        return this;
    }


}
