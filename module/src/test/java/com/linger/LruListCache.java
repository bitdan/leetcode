package com.linger;

import java.util.LinkedList;

/**
 * @version 1.0
 * @description test
 * @date 2024/8/13 15:37:19
 */
public class LruListCache<E> {
    private final int capacity;
    private LinkedList<E> list = new LinkedList<>();

    public LruListCache(int capacity) {
        this.capacity = capacity;
    }

    public void add(E e) {
        if (list.size() < capacity) {
            list.addFirst(e);
        } else {
            list.removeLast();
            list.addFirst(e);
        }
    }

    public E get(int index) {
        E e = list.get(index);
        list.remove(e);
        add(e);
        return e;
    }


    @Override
    public String toString() {
        return list.toString();
    }
}
