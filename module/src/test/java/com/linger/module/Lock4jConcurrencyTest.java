package com.linger.module;

import com.linger.OOOOApplication;
import com.linger.module.service.QuotationService;
import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * @version 1.0
 * @description Lock4jConcurrencyTest
 * @date 2025/7/10 09:58:56
 */
@Slf4j
@SpringBootTest(classes = OOOOApplication.class)
public class Lock4jConcurrencyTest {

    @Autowired
    private QuotationService quotationService;

    @Test
    public void testConcurrentLocking() throws InterruptedException {
        String sku = "SKU123";

        int threadCount = 10; // 模拟10个线程
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch latch = new CountDownLatch(threadCount);

        Runnable task = () -> {
            try {
                log.info(">>> 线程 {} 尝试调用 createQuotation", Thread.currentThread().getName());
                quotationService.createQuotation(sku);
                log.info("<<< 线程 {} 执行完毕", Thread.currentThread().getName());
            } catch (Exception e) {
                log.error("线程 {} 出现异常", Thread.currentThread().getName(), e);
            } finally {
                latch.countDown();
            }
        };

        // 启动多个线程并发执行
        for (int i = 0; i < threadCount; i++) {
            executor.submit(task);
        }

        // 等待所有线程完成
        latch.await();
        executor.shutdown();
    }
}
