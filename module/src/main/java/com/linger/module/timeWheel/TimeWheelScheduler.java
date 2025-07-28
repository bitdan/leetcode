package com.linger.module.timeWheel;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * 时间轮调度器，提供便捷的API来使用时间轮
 */
public class TimeWheelScheduler {

    private final TimeWheel timeWheel;
    private final ExecutorService taskExecutor;
    private volatile boolean started = false;

    /**
     * 创建时间轮调度器
     *
     * @param tickMs    每个时间格子的毫秒数
     * @param wheelSize 时间轮大小
     */
    public TimeWheelScheduler(long tickMs, int wheelSize) {
        this.timeWheel = new TimeWheel(tickMs, wheelSize, System.currentTimeMillis());
        this.taskExecutor = Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors());
    }

    /**
     * 创建默认的时间轮调度器（100ms精度，100个格子）
     */
    public TimeWheelScheduler() {
        this(100L, 100);
    }

    /**
     * 启动调度器
     */
    public synchronized void start() {
        if (!started) {
            timeWheel.start();
            started = true;
        }
    }

    /**
     * 停止调度器
     */
    public synchronized void stop() {
        if (started) {
            timeWheel.stop();
            taskExecutor.shutdown();
            started = false;
        }
    }

    /**
     * 延迟执行任务
     *
     * @param delay 延迟时间
     * @param unit  时间单位
     * @param task  要执行的任务
     */
    public void schedule(long delay, TimeUnit unit, Runnable task) {
        if (!started) {
            throw new IllegalStateException("Scheduler is not started");
        }

        long delayMs = unit.toMillis(delay);
        TimerTask timerTask = new TimerTask(delayMs, () -> {
            try {
                taskExecutor.submit(task);
            } catch (Exception e) {
                e.printStackTrace();
            }
        });

        boolean added = timeWheel.addTask(timerTask);
        if (!added) {
            // 如果任务无法添加到时间轮（已过期），立即执行
            taskExecutor.submit(task);
        }
    }

    /**
     * 延迟执行任务并返回CompletableFuture
     *
     * @param delay 延迟时间
     * @param unit  时间单位
     * @param task  要执行的任务
     * @return CompletableFuture
     */
    public CompletableFuture<Void> scheduleAsync(long delay, TimeUnit unit, Runnable task) {
        CompletableFuture<Void> future = new CompletableFuture<>();
        schedule(delay, unit, () -> {
            try {
                task.run();
                future.complete(null);
            } catch (Exception e) {
                future.completeExceptionally(e);
            }
        });
        return future;
    }

    /**
     * 延迟执行任务并返回结果
     *
     * @param delay    延迟时间
     * @param unit     时间单位
     * @param supplier 要执行的任务
     * @param <T>      返回类型
     * @return CompletableFuture
     */
    public <T> CompletableFuture<T> scheduleAsync(long delay, TimeUnit unit, java.util.function.Supplier<T> supplier) {
        CompletableFuture<T> future = new CompletableFuture<>();
        schedule(delay, unit, () -> {
            try {
                T result = supplier.get();
                future.complete(result);
            } catch (Exception e) {
                future.completeExceptionally(e);
            }
        });
        return future;
    }

    /**
     * 检查调度器是否已启动
     */
    public boolean isStarted() {
        return started;
    }

    /**
     * 获取时间轮当前时间
     */
    public long getCurrentTime() {
        return timeWheel.getCurrentTime();
    }

    /**
     * 获取时间轮大小
     */
    public int getWheelSize() {
        return timeWheel.getWheelSize();
    }

    /**
     * 获取时间轮间隔
     */
    public long getInterval() {
        return timeWheel.getInterval();
    }
} 
