package com.linger.module.annotation;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;

import javax.annotation.Resource;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

@SpringBootTest
@TestPropertySource(properties = {
        "spring.redis.host=localhost",
        "spring.redis.port=6379",
        "spring.redis.database=0"
})
public class RedisLockAspectTest {

    @Resource
    private TestLockService testLockService;

    @Resource
    private TestLockService testBusinessService;

    // 测试1: 基本锁功能测试
    @Test
    public void testRedisLockAspect() throws InterruptedException {
        int threadCount = 10;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch latch = new CountDownLatch(threadCount);

        for (int i = 0; i < threadCount; i++) {
            executor.submit(() -> {
                try {
                    testLockService.doBusiness();
                } catch (Exception ignored) {
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();

        int executedTimes = testLockService.getCount();
        System.out.println("业务执行次数 = " + executedTimes);

        Assertions.assertEquals(1, executedTimes);
        executor.shutdown();
    }

    // 测试2: 固定key锁测试
    @Test
    public void testFixedKeyLock() throws InterruptedException {
        AtomicInteger successCount = new AtomicInteger(0);
        int threadCount = 5;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch latch = new CountDownLatch(threadCount);

        for (int i = 0; i < threadCount; i++) {
            executor.submit(() -> {
                try {
                    testBusinessService.fixedKey();
                    successCount.incrementAndGet();
                } catch (Exception e) {
                    System.out.println("预期中的限流: " + e.getMessage());
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();
        System.out.println("成功执行次数: " + successCount.get());

        // 由于interval=2秒，快速连续调用应该只有1次成功
        Assertions.assertEquals(1, successCount.get());
        executor.shutdown();
    }

    // 测试3: SpEL参数锁测试
    @Test
    public void testSpELParameterLock() throws InterruptedException {
        AtomicInteger successCount = new AtomicInteger(0);
        int threadCount = 6;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch latch = new CountDownLatch(threadCount);

        // 测试不同参数可以并发执行
        for (int i = 0; i < threadCount; i++) {
            final Long userId = (i % 2 == 0) ? 1001L : 1002L; // 两个不同的用户ID
            executor.submit(() -> {
                try {
                    testBusinessService.withSpEL(userId);
                    successCount.incrementAndGet();
                } catch (Exception e) {
                    System.out.println("执行失败: " + e.getMessage());
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();
        System.out.println("成功执行次数: " + successCount.get());

        // 两个不同的用户ID应该都能成功执行
        Assertions.assertTrue(successCount.get() >= 2);
        executor.shutdown();
    }

    // 测试4: 相同参数锁测试
    @Test
    public void testSameParameterLock() throws InterruptedException {
        AtomicInteger successCount = new AtomicInteger(0);
        int threadCount = 5;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch latch = new CountDownLatch(threadCount);

        // 所有线程使用相同的参数
        for (int i = 0; i < threadCount; i++) {
            executor.submit(() -> {
                try {
                    testBusinessService.withSpEL(2001L); // 相同的用户ID
                    successCount.incrementAndGet();
                } catch (Exception e) {
                    System.out.println("预期中的锁竞争: " + e.getMessage());
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();
        System.out.println("成功执行次数: " + successCount.get());

        // 相同参数应该只有1次成功
        Assertions.assertEquals(1, successCount.get());
        executor.shutdown();
    }

    // 测试5: 集合参数锁测试
    @Test
    public void testCollectionParameterLock() throws InterruptedException {
        AtomicInteger successCount = new AtomicInteger(0);
        int threadCount = 4;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch latch = new CountDownLatch(threadCount);

        // 测试集合参数
        java.util.List<Long> ids = java.util.Arrays.asList(3001L, 3002L, 3003L);

        for (int i = 0; i < threadCount; i++) {
            final java.util.List<Long> paramIds = (i % 2 == 0) ?
                    java.util.Arrays.asList(3001L, 3002L) :
                    java.util.Arrays.asList(3003L, 3004L);

            executor.submit(() -> {
                try {
                    testBusinessService.batchProcess(paramIds);
                    successCount.incrementAndGet();
                } catch (Exception e) {
                    System.out.println("执行失败: " + e.getMessage());
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();
        System.out.println("成功执行次数: " + successCount.get());
        executor.shutdown();
    }


    // 测试6: 复杂SpEL表达式测试
    @Test
    public void testComplexSpELLock() throws InterruptedException {
        AtomicInteger successCount = new AtomicInteger(0);
        int threadCount = 4;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch latch = new CountDownLatch(threadCount);

        for (int i = 0; i < threadCount; i++) {
            final Order order = new Order(4000L + i, "订单" + i);
            executor.submit(() -> {
                try {
                    testBusinessService.updateOrder(order);
                    successCount.incrementAndGet();
                } catch (Exception e) {
                    System.out.println("执行失败: " + e.getMessage());
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();
        System.out.println("成功执行次数: " + successCount.get());

        // 不同订单应该都能成功执行
        Assertions.assertEquals(threadCount, successCount.get());
        executor.shutdown();
    }

    // 测试7: 默认key锁测试
    @Test
    public void testDefaultKeyLock() throws InterruptedException {
        AtomicInteger successCount = new AtomicInteger(0);
        int threadCount = 5;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch latch = new CountDownLatch(threadCount);

        for (int i = 0; i < threadCount; i++) {
            executor.submit(() -> {
                try {
                    testBusinessService.defaultKey();
                    successCount.incrementAndGet();
                } catch (Exception e) {
                    System.out.println("预期中的限流: " + e.getMessage());
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();
        System.out.println("成功执行次数: " + successCount.get());

        // 由于interval=5秒，快速连续调用应该只有1次成功
        Assertions.assertEquals(1, successCount.get());

        // 等待interval过期后再次测试
        Thread.sleep(6000);
        testBusinessService.defaultKey(); // 应该成功
        executor.shutdown();
    }

    // 测试8: 间隔时间测试
    @Test
    public void testIntervalLimit() throws InterruptedException {
        // 第一次调用应该成功
        testBusinessService.fixedKey();

        // 立即第二次调用应该被限流
        try {
            testBusinessService.fixedKey();
            Assertions.fail("应该抛出限流异常");
        } catch (Exception e) {
            System.out.println("预期中的限流: " + e.getMessage());
        }

        // 等待3秒后应该可以再次调用
        Thread.sleep(3000);
        testBusinessService.fixedKey(); // 应该成功
    }
}
