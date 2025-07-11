package com.linger;

import java.util.*;

/**
 * @version 1.0
 * @description test
 * @date 2024/8/13 16:48:24
 */
public class MyHashMap<K, V> {
    private static final int DEFAULT_INITIAL_CAPACITY = 16;
    private static final float DEFAULT_LOAD_FACTOR = 0.75f;

    private static class Node<K, V> {
        final K key;
        V value;
        Node<K, V> next;

        public Node(K key, V value) {
            this.key = key;
            this.value = value;
        }
    }

    private Node<K, V>[] table;
    private int size;
    private int threshold;

    public MyHashMap() {
        this.table = new Node[DEFAULT_INITIAL_CAPACITY];
        this.threshold = (int) (DEFAULT_LOAD_FACTOR * DEFAULT_INITIAL_CAPACITY);
    }

    private int hash(K key) {
        return key == null ? 0 : key.hashCode() & (table.length - 1);
    }

    public void put(K key, V value) {
        int hash = hash(key);
        Node<K, V> node = table[hash];

        if (node == null) {
            table[hash] = new Node<>(key, value);
        } else {
            while (node != null) {
                if (key.equals(node.key)) {
                    node.value = value;
                    return;
                }
                if (node.next == null) {
                    node.next = new Node<>(key, value);
                    break;
                }
                node = node.next;
            }
        }
        size++;
        if (size >= threshold) {
            resize();
        }
    }

    public V get(K key) {
        int hash = hash(key);
        Node<K, V> node = table[hash];
        while (node != null) {
            if (Objects.equals(node.key, key)) {
                return node.value;
            }
            node = node.next;
        }
        return null;
    }

    public V remove(K key) {
        int hash = hash(key);
        Node<K, V> node = table[hash];
        Node<K, V> prev = null;
        while (node != null) {
            if (Objects.equals(node.key, key)) {
                if (prev != null) {
                    prev.next = node.next;
                } else {
                    table[hash] = node.next;
                }
                size--;
                return node.value;
            }
            prev = node;
            node = node.next;

        }
        return null;
    }

    private void resize() {
        Node<K, V>[] oldTable = table;
        table = new Node[oldTable.length * 2];
        threshold = (int) (table.length * DEFAULT_LOAD_FACTOR);
        size = 0;

        for (Node<K, V> node : oldTable) {
            while (node != null) {
                put(node.key, node.value);
                node = node.next;
            }
        }
    }

    public int size() {
        return size;
    }

    public boolean isEmpty() {
        return size == 0;
    }

    public void clear() {
        size = 0;
        table = new Node[DEFAULT_INITIAL_CAPACITY];
        threshold = (int) (DEFAULT_LOAD_FACTOR * DEFAULT_INITIAL_CAPACITY);
    }

    public boolean containsKey(K key) {
        int hash = hash(key);
        Node<K, V> node = table[hash];
        while (node != null) {
            if (Objects.equals(node.key, key)) {
                return true;
            }
            node = node.next;
        }
        return false;
    }

    public boolean containsValue(V value) {
        for (Node<K, V> node : table) {
            while (node != null) {
                if (Objects.equals(node.value, value)) {
                    return true;
                }
                node = node.next;
            }
        }
        return false;
    }

    public Set<K> keySet() {
        Set<K> keySet = new HashSet<>();
        for (Node<K, V> node : table) {
            while (node != null) {
                keySet.add(node.key);
                node = node.next;
            }
        }
        return keySet;
    }

    public Collection<V> values() {
        ArrayList<V> values = new ArrayList<>();
        for (Node<K, V> node : table) {
            while (node != null) {
                values.add(node.value);
                node = node.next;
            }
        }
        return values;
    }

    public Set<Map.Entry<K, V>> entrySet() {
        Set<Map.Entry<K, V>> entrySet = new HashSet<>();
        for (Node<K, V> node : table) {
            while (node != null) {
                entrySet.add(new AbstractMap.SimpleEntry<>(node.key, node.value));
                node = node.next;
            }
        }
        return entrySet;
    }
}
