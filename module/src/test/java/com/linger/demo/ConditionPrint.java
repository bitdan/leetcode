package com.linger.demo;

import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

/**
 * @description ConditionPrint
 * @date 2026/3/30 17:38:31
 * @version 1.0
 */
@Slf4j
public class ConditionPrint {
    private static final Lock lock = new ReentrantLock();
    private final Condition[] conditions;
    private int n;
    private int count = 1;


    public ConditionPrint(int n) {
        this.n = n;
        this.conditions = new Condition[n];
        for (int i = 0; i < n; i++) {
            conditions[i] = lock.newCondition();
        }
    }

    public static void main(String[] args) {
        int threadNum = 2;
        ConditionPrint conditionPrint = new ConditionPrint(threadNum);
        int max = 100;
        String[] names = new String[]{"A", "B"};
        for (int i = 0; i < threadNum; i++) {
            int index = i;
            new Thread(() -> conditionPrint.print(index, names[index], max)).start();
        }
    }

    private void print(int i, String name, int max) {
        while (true) {
            lock.lock();
            try {
                while ((count - 1) % n != i && count <= max) {
                    conditions[i].await();
                }
                if (count > max) {
                    for (Condition condition : conditions) {
                        condition.signalAll();
                    }
                    return;
                }
                log.info("线程{}--{}-- {}", i, name, count);
                count++;
                conditions[(i + 1) % n].signal();
            } catch (InterruptedException e) {
                e.printStackTrace();
                return;
            } finally {
                lock.unlock();
            }
        }
    }
}
