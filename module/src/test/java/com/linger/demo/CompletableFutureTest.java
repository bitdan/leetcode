package com.linger.demo;

import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;

import java.util.Random;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
public class CompletableFutureTest {
    private class CustomThreadFactory implements ThreadFactory {

        private AtomicInteger count = new AtomicInteger(0);

        @Override
        public Thread newThread(Runnable r) {
            Thread t = new Thread(r);
            String threadName = CompletableFutureTest.class.getSimpleName() + count.addAndGet(1);
            log.info(threadName);
            t.setName(threadName);
            return t;
        }
    }


    private class CustomRejectedExecutionHandler implements RejectedExecutionHandler {

        @Override
        public void rejectedExecution(Runnable r, ThreadPoolExecutor executor) {
            // 记录异常
            // 报警处理等
            log.info("error.............");
        }
    }

    ThreadPoolExecutor pool = new ThreadPoolExecutor(
        10,
        30,
        30,
        TimeUnit.MINUTES,
        new ArrayBlockingQueue<Runnable>(10), //有界队列
        new CustomThreadFactory(),
        new ThreadPoolExecutor.AbortPolicy());

    //无返回值
    @Test
    public void testRunAsync() throws Exception {
        CompletableFuture<Void> future = CompletableFuture.runAsync(() -> {
            try {
                TimeUnit.SECONDS.sleep(1);
            } catch (InterruptedException e) {
            }
            log.info("run end ...");
        }, pool).thenRunAsync(() -> {
            log.info("whoe is : {}", "whoe");
        }, pool);

        future.get();
    }

    //有返回值
    @Test
    public void testSupplyAsync() throws Exception {
        CompletableFuture<Long> future = CompletableFuture.supplyAsync(() -> {
            try {
                TimeUnit.SECONDS.sleep(1);
            } catch (InterruptedException e) {
            }
            log.info("run end ...");
            return System.currentTimeMillis();
        });

        long time = future.get();
        log.info("time = {}", time);
    }

    @Test
    public void testWhenComplete() throws Exception {
        CompletableFuture<Void> future = CompletableFuture.runAsync(() -> {
                try {
                    TimeUnit.SECONDS.sleep(1);
                } catch (InterruptedException e) {
                }
                if (new Random().nextInt() % 2 >= 0) {
                    int i = 12 / 2;
                }
                log.info("{}, run end ...", Thread.currentThread().getName());
            }).whenCompleteAsync((t, action) -> log.info(Thread.currentThread().getName() + ", whenComplete 1 执行完成！"))
            .whenCompleteAsync((t, action) -> log.info(Thread.currentThread().getName() + ", whenComplete 2 执行完成！"))
            .exceptionally(t -> {
                log.info("{}, 执行失败！{}", Thread.currentThread().getName(), t.getMessage());
                return null;
            });
        future.get();
//        TimeUnit.SECONDS.sleep(2);
    }

    @Test
    public void testThenApply() throws Exception {
        CompletableFuture<Long> future = CompletableFuture.supplyAsync(() -> {
            long result = new Random().nextInt(100);
            log.info("{}, result1={}", Thread.currentThread().getName(), result);
            return result;
        }).thenApplyAsync(t -> {
            long result = t * 5;
            log.info("{}, result2={}", Thread.currentThread().getName(), result);
            return result;
        });

        long result = future.get();
        log.info(Thread.currentThread().getName() + ", result=" + result);
    }

    @Test
    void testHandle() throws Exception {
        CompletableFuture<Integer> future = CompletableFuture.supplyAsync(() -> {
            log.info(Thread.currentThread().getName() + ", in async task");
            int i = 10 / 0;
            return new Random().nextInt(10);
        }).handle((param, throwable) -> {
            int result = -1;
            if (throwable == null) {
                result = param * 2;
            } else {
                log.info(Thread.currentThread().getName() + "," + throwable.getMessage());
            }
            return result;
        });
        log.info("{},{}", Thread.currentThread().getName(), future.get());
    }

    @Test
    public void testThenAccept() throws Exception {
        CompletableFuture<Void> future = CompletableFuture.supplyAsync(() -> {
            log.info(Thread.currentThread().getName() + ", in async task");
            return new Random().nextInt(10);
        }).thenAccept(integer -> {
            log.info("{}, integer={}", Thread.currentThread().getName(), integer);
        });
        future.get();
        log.info("{}, caller", Thread.currentThread().getName());
    }

    @Test
    void testThenRun() throws Exception {
        CompletableFuture<Integer> future = CompletableFuture.supplyAsync(() -> {
            log.info(Thread.currentThread().getName() + ", in async task");
            return new Random().nextInt(10);
        }).thenApplyAsync((res) -> {
            log.info("{}, in thenRun {}", Thread.currentThread().getName(), res);
            return res;
        });
        Integer i = future.get();
        log.info("i is : {}", i);
    }

    @Test
    void thenCombine() throws Exception {
        CompletableFuture<String> future1 = CompletableFuture.supplyAsync(() -> {
            log.info("{}, in async task 1", Thread.currentThread().getName());
            return "hello";
        });
        CompletableFuture<String> future2 = CompletableFuture.supplyAsync(() -> {
            log.info("{}, in async task 2", Thread.currentThread().getName());
            return "world";
        });
        CompletableFuture<String> result = future1.thenCombineAsync(future2, (t, u) -> {
            log.info("{}, in combine task", Thread.currentThread().getName());
            return t + " " + u;
        });
        log.info("{},{}", Thread.currentThread().getName(), result.get());
    }
}
