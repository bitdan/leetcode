package com.linger.module.util;


import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

import javax.annotation.Resource;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.stream.IntStream;

/**
 * @description RedisUtilTest
 * @date 2025/12/11 18:12:15
 * @version 1.0
 */


@SpringBootTest
public class RedisUtilTest {

    @Resource
    private RedisUtil redisUtil;

    /**
     * 单线程简单测试
     */
    @Test
    void testSingle() {
        String orderNo = redisUtil.getOrderSerialNumber(
                "ORDER_SERIAL",  // Redis key 前缀
                "OD",            // 前缀
                "yyyyMMdd",      // 日期格式
                6                // 序列号位数
        );
        System.out.println(orderNo);
    }

    /**
     * 多线程并发测试，验证是否重复
     */
    @Test
    void testConcurrent() throws InterruptedException {

        int threadCount = 20;   // 开多少线程
        int createCount = 100;  // 每线程创建多少个订单号

        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        Set<String> results = ConcurrentHashMap.newKeySet();

        CountDownLatch latch = new CountDownLatch(threadCount);

        IntStream.range(0, threadCount).forEach(i -> {
            executor.submit(() -> {
                try {
                    for (int j = 0; j < createCount; j++) {
                        String orderNo = redisUtil.getOrderSerialNumber(
                                "ORDER_SERIAL",
                                "OD",
                                "yyyyMMdd",
                                6
                        );
                        results.add(orderNo);
                        System.out.println(orderNo);
                    }
                } finally {
                    latch.countDown();
                }
            });
        });

        latch.await();
        executor.shutdown();

        // 校验是否有重复
        int expected = threadCount * createCount;
        int actual = results.size();

        System.out.println("预期生成数量 = " + expected);
        System.out.println("实际生成数量 = " + actual);

        if (expected != actual) {
            System.err.println("❌ 存在重复订单号！");
        } else {
            System.out.println("✔ 无重复，测试通过！");
        }
    }
}
