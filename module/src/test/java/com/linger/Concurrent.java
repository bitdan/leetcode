package com.linger;

import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.ReentrantLock;

/**
 * @version 1.0
 * @description concurrent
 * @date 2024/7/28 16:47:58
 */
@Slf4j
public class Concurrent {
    public static final Object Lock = new Object();
    public static volatile int count = 0;
    public static final int max = 100;
    public static final ReentrantLock reentrantLock = new ReentrantLock();
    private static final AtomicInteger currentNum = new AtomicInteger(1);
    private static final String[] LETTERS = {"A", "B", "C"};
    private static Boolean isOdd = true;
    private static volatile Concurrent singleton;

    private Concurrent() {
    }

    public static Concurrent getSingleton() {
        if (singleton == null) {
            synchronized (Concurrent.class) {
                if (singleton == null) {
                    singleton = new Concurrent();
                }
            }
        }
        return singleton;
    }

    @Test
    public void synchronizedTest() {
        Thread thread = new Thread(new Seq(0));
        Thread thread1 = new Thread(new Seq(1));
        Thread thread2 = new Thread(new Seq(2));
        thread.start();
        thread1.start();
        thread2.start();
    }

    @Test
    public void synchronizedTest2() {
        Thread thread = new Thread(new Seq2(0));
        Thread thread1 = new Thread(new Seq2(1));
        thread.start();
        thread1.start();
    }

    @Test
    public void synchronizedTestABC() {
        Thread thread = new Thread(new SeqABC(0));
        Thread thread1 = new Thread(new SeqABC(1));
        Thread thread2 = new Thread(new SeqABC(2));
        thread.start();
        thread1.start();
        thread2.start();
    }

    @Test
    public void synchronizedNumberLetter() {
        Thread thread = new Thread(new NumberPrint());
        Thread thread1 = new Thread(new LetterPrint());
        thread.start();
        thread1.start();
    }

    @Test
    public void synchronizedOddEven() {
        Thread thread = new Thread(new OddPrint());
        Thread thread1 = new Thread(new EvenPrint());
        thread.start();
        thread1.start();
    }


    @Test
    public void reentrantLockTest() {
        final ArrayList<Condition> conditions = new ArrayList<>();
        for (int i = 0; i < 3; i++) {
            Condition condition = reentrantLock.newCondition();
            conditions.add(condition);
            Worker worker = new Worker(i, conditions);
            worker.start();
        }
    }

    @Test
    public void completableFutureTest() {
        ExecutorService executor = Executors.newFixedThreadPool(3);

        CompletableFuture<Void> task1 = CompletableFuture.runAsync(new Printer(0), executor);
        CompletableFuture<Void> task2 = CompletableFuture.runAsync(new Printer(1), executor);
        CompletableFuture<Void> task3 = CompletableFuture.runAsync(new Printer(2), executor);

        CompletableFuture.allOf(task1, task2, task3).join();

        executor.shutdown();
    }

    private ArrayList<Integer> list = new ArrayList<>();

    public void add(int value) {
        synchronized (Concurrent.class) {
            list.add(value);
        }
    }

    public int get(int index) {
        synchronized (Concurrent.class) {
            return list.get(index);
        }
    }

    static class NumberPrint implements Runnable {
        @Override
        public void run() {
            synchronized (Lock) {
                for (int i = 1; i <= 3; i++) {
                    try {
                        while (!isOdd) {
                            Lock.wait();
                        }
                        log.info(String.valueOf(i));
                        isOdd = false;
                        Lock.notifyAll();
                    } catch (InterruptedException e) {
                        throw new RuntimeException(e);
                    }
                }

            }

        }
    }

    static class LetterPrint implements Runnable {
        @Override
        public void run() {

            synchronized (Lock) {
                for (char i = 'A'; i <= 'C'; i++) {
                    try {
                        while (isOdd) {
                            Lock.wait();
                        }
                        log.info(String.valueOf(i));
                        isOdd = true;
                        Lock.notify();
                    } catch (InterruptedException e) {
                        throw new RuntimeException(e);
                    }
                }

            }

        }
    }

    static class OddPrint implements Runnable {
        @Override
        public void run() {
            synchronized (Lock) {
                while (count < max) {
                    if (count % 2 == 0) {
                        try {
                            Lock.wait();
                        } catch (InterruptedException e) {
                            throw new RuntimeException(e);
                        }
                    } else {
                        log.info("thread odd --{}", count);
                        count++;
                        Lock.notifyAll();
                    }
                }
            }
        }
    }

    static class EvenPrint implements Runnable {
        @Override
        public void run() {
            synchronized (Lock) {
                while (count < max) {
                    if (count % 2 == 1) {
                        try {
                            Lock.wait();
                        } catch (InterruptedException e) {
                            throw new RuntimeException(e);
                        }

                    } else {
                        log.info("thread even --{}", count);
                        count++;
                        Lock.notifyAll();
                    }
                }

            }
        }
    }

    static class Seq implements Runnable {
        private final int index;

        public Seq(int index) {
            this.index = index;
        }

        @Override
        public void run() {
            while (count < max) {
                synchronized (Lock) {
                    try {
                        while (count % 3 != index) {
                            Lock.wait();
                        }
                        if (count <= max) {
                            log.info("thread-{}-count-{}", index, count);
                        }
                        count++;
                        Lock.notifyAll();
                    } catch (InterruptedException e) {
                        e.printStackTrace();
                    }
                }
            }
        }
    }

    static class Seq2 implements Runnable {
        private final int index;

        public Seq2(int index) {
            this.index = index;
        }

        @Override
        public void run() {
            while (count < max) {
                synchronized (Lock) {
                    try {
                        while (count % 2 != index) {
                            Lock.wait();
                        }
                        if (count <= max) {
                            log.info("thread-{}-count-{}", index, count);
                        }
                        count++;
                        Lock.notifyAll();
                    } catch (InterruptedException e) {
                        e.printStackTrace();
                    }
                }
            }
        }
    }

    static class SeqABC implements Runnable {
        private final int index;

        public SeqABC(int index) {
            this.index = index;
        }

        @Override
        public void run() {
            while (count < max) {
                synchronized (Lock) {
                    try {
                        while (count % 3 != index) {
                            Lock.wait();
                        }
                        if (count <= max) {
                            log.info("thread-{}-count-{}", index, LETTERS[index]);
                        }
                        count++;
                        Lock.notifyAll();
                    } catch (InterruptedException e) {
                        e.printStackTrace();
                    }
                }
            }
        }
    }

    static class Worker extends Thread {
        int index;
        List<Condition> conditions;

        public Worker(int index, List<Condition> conditions) {
            super("Thread-" + index);
            this.index = index;
            this.conditions = conditions;
        }

        private void signalNext() {
            int indexNext = (index + 1) % conditions.size();
            conditions.get(indexNext).signal();
        }

        @Override
        public void run() {
            while (true) {
                reentrantLock.lock();
                try {
                    if (conditions.size() % 3 != index) {
                        conditions.get(index).await();
                    }
                    if (count > 100) {
                        signalNext();
                        return;
                    }
                    log.info("{}{}", this.getName(), count);
                    count++;
                    signalNext();
                } catch (InterruptedException e) {
                    e.printStackTrace();
                } finally {
                    reentrantLock.unlock();
                }
            }
        }
    }

    static class Printer implements Runnable {
        private final int threadId;
        private static final Object lock = new Object();

        Printer(int threadId) {
            this.threadId = threadId;
        }

        @Override
        public void run() {
            while (true) {
                synchronized (lock) {
                    if (currentNum.get() > max) {
                        break;
                    }
                    if (currentNum.get() % 3 == threadId) {
                        log.info("{}: {}", Thread.currentThread().getName(), currentNum.getAndIncrement());
                        lock.notifyAll();
                    } else {
                        try {
                            lock.wait();
                        } catch (InterruptedException e) {
                            Thread.currentThread().interrupt();
                        }
                    }
                }
            }
        }
    }

}
