//
// 请你设计并实现一个满足 
// LRU (最近最少使用) 缓存 约束的数据结构。
// 
//
// 
// 实现 
// LRUCache 类：
// 
//
// 
// 
// 
// LRUCache(int capacity) 以 正整数 作为容量 capacity 初始化 LRU 缓存 
// int get(int key) 如果关键字 key 存在于缓存中，则返回关键字的值，否则返回 -1 。 
// void put(int key, int value) 如果关键字 key 已经存在，则变更其数据值 value ；如果不存在，则向缓存中插入该组 
//key-value 。如果插入操作导致关键字数量超过 capacity ，则应该 逐出 最久未使用的关键字。 
// 
// 
// 
//
// 函数 get 和 put 必须以 O(1) 的平均时间复杂度运行。 
//
// 
//
// 示例： 
//
// 
//输入
//["LRUCache", "put", "put", "get", "put", "get", "put", "get", "get", "get"]
//[[2], [1, 1], [2, 2], [1], [3, 3], [2], [4, 4], [1], [3], [4]]
//输出
//[null, null, null, 1, null, -1, null, -1, 3, 4]
//
//解释
//LRUCache lRUCache = new LRUCache(2);
//lRUCache.put(1, 1); // 缓存是 {1=1}
//lRUCache.put(2, 2); // 缓存是 {1=1, 2=2}
//lRUCache.get(1);    // 返回 1
//lRUCache.put(3, 3); // 该操作会使得关键字 2 作废，缓存是 {1=1, 3=3}
//lRUCache.get(2);    // 返回 -1 (未找到)
//lRUCache.put(4, 4); // 该操作会使得关键字 1 作废，缓存是 {4=4, 3=3}
//lRUCache.get(1);    // 返回 -1 (未找到)
//lRUCache.get(3);    // 返回 3
//lRUCache.get(4);    // 返回 4
// 
//
// 
//
// 提示： 
//
// 
// 1 <= capacity <= 3000 
// 0 <= key <= 10000 
// 0 <= value <= 10⁵ 
// 最多调用 2 * 10⁵ 次 get 和 put 
// 
//
// Related Topics 设计 哈希表 链表 双向链表 👍 3596 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

import java.util.HashMap;
import java.util.Map;

@Slf4j
public class LruCache {

    class Node {
        int key;
        int value;
        Node pre;
        Node next;

        public Node() {
        }

        public Node(int key, int value) {
            this.key = key;
            this.value = value;
        }
    }

    private Node head = new Node();
    private Node tail = new Node();
    private int capacity;
    private Map<Integer, Node> map = new HashMap<>();

    public LruCache(int capacity) {
        this.capacity = capacity;
        head.next = tail;
        tail.pre = head;
    }

    public int get(int key) {
        Node node = map.get(key);
        if (node != null) {
            removeNode(node);
            addToHdead(node);
            return node.value;
        }
        return -1;
    }

    private void addToHdead(Node node) {
        node.pre = head;
        node.next = head.next;
        head.next.pre = node;
        head.next = node;
    }

    private void removeNode(Node node) {
        node.pre.next = node.next;
        node.next.pre = node.pre;
    }

    public void put(int key, int value) {
        Node node = map.get(key);
        if (node != null) {
            removeNode(node);
            node.value = value;
            addToHdead(node);
        } else {
            Node node1 = new Node(key, value);
            addToHdead(node1);
            map.put(key, node1);
            if (map.size() > capacity) {
                Node tailPre = tail.pre;
                removeNode(tailPre);
                map.remove(tailPre.key);
            }
        }
    }


    public static void main(String[] args) {

        LruCache lruCache = new LruCache(2);
        lruCache.put(1, 1); // 缓存是 {1=1}
        lruCache.put(2, 2); // 缓存是 {1=1, 2=2}
        System.out.println(lruCache.get(1)); // 返回 1
        lruCache.put(3, 3); // 淘汰 key=2，缓存是 {1=1, 3=3}
        System.out.println(lruCache.get(2)); // 返回 -1
        lruCache.put(4, 4); // 淘汰 key=1，缓存是 {4=4, 3=3}
        System.out.println(lruCache.get(1)); // 返回 -1
        System.out.println(lruCache.get(3)); // 返回 3
        System.out.println(lruCache.get(4)); // 返回 4
    }

}
