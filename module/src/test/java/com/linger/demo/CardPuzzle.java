package com.linger.demo;

import java.util.*;

/**
 * @description CardPuzzle
 * @date 2026/3/16 16:05:17
 * @version 1.0
 */
public class CardPuzzle {
    public static void main(String[] args) {
        List<Integer> result = Arrays.asList(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13);

        // 逆向推导初始牌堆
        List<Integer> initialDeck = backward(result);

        System.out.println("初始牌堆顺序: " + initialDeck);
    }

    /**
     * 已知翻牌顺序，逆向推导初始牌堆
     */
    private static List<Integer> backward(List<Integer> result) {
        Deque<Integer> deque = new LinkedList<>();

        for (int i = result.size() - 1; i >= 0; i--) {
            // 逆操作1：把底部移到顶部
            if (!deque.isEmpty()) {
                Integer last = deque.removeLast();
                deque.addFirst(last);
            }

            // 逆操作2：把当前牌放到顶部
            deque.addFirst(result.get(i));
        }

        return new ArrayList<>(deque);
    }
}
