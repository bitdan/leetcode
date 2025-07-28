package com.linger.module;

import com.linger.module.timeWheel.TimeWheelScheduler;
import org.junit.jupiter.api.Test;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 简单的时间轮测试
 */
public class SimpleTimeWheelTest {

    @Test
    public void testSimpleScheduling() throws InterruptedException {
        System.out.println("开始测试简单调度...");

        TimeWheelScheduler scheduler = new TimeWheelScheduler();
        scheduler.start();

        CountDownLatch latch = new CountDownLatch(1);
        AtomicInteger counter = new AtomicInteger(0);

        System.out.println("调度任务，延迟1秒执行...");
        scheduler.schedule(1, TimeUnit.SECONDS, () -> {
            System.out.println("任务执行了！时间: " + System.currentTimeMillis());
            counter.incrementAndGet();
            latch.countDown();
        });

        System.out.println("等待任务执行...");
        boolean completed = latch.await(3, TimeUnit.SECONDS);

        System.out.println("任务完成状态: " + completed);
        System.out.println("计数器值: " + counter.get());

        scheduler.stop();
        System.out.println("测试完成");
    }

    @Test
    public void testMultipleTasks() throws InterruptedException {
        System.out.println("开始测试多个任务...");

        TimeWheelScheduler scheduler = new TimeWheelScheduler();
        scheduler.start();

        CountDownLatch latch = new CountDownLatch(3);
        AtomicInteger counter = new AtomicInteger(0);

        // 调度3个任务
        for (int i = 1; i <= 3; i++) {
            final int taskId = i;
            scheduler.schedule(i, TimeUnit.SECONDS, () -> {
                System.out.println("任务 " + taskId + " 执行了！时间: " + System.currentTimeMillis());
                counter.incrementAndGet();
                latch.countDown();
            });
        }

        System.out.println("等待所有任务执行...");
        boolean completed = latch.await(5, TimeUnit.SECONDS);

        System.out.println("所有任务完成状态: " + completed);
        System.out.println("最终计数器值: " + counter.get());

        scheduler.stop();
        System.out.println("测试完成");
    }
} 
