package com.linger.module.annotation;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

import javax.annotation.Resource;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * @description RedisLockAspectTest
 * @date 2025/12/11 18:27:10
 * @version 1.0
 */
@SpringBootTest
public class RedisLockAspectTest {


    @Resource
    private TestLockService testLockService;

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
}
