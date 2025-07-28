package com.linger.module.timeWheel;

import java.util.concurrent.DelayQueue;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 轻量级时间轮实现
 * 支持毫秒级精度的定时任务调度
 */
public class TimeWheel {

    private final long tickMs; // 每个时间格子的毫秒数
    private final int wheelSize; // 时间轮大小
    private final long interval; // 时间轮总间隔
    private final long startTime; // 启动时间

    private final AtomicLong currentTime; // 当前时间
    private final TimeWheelBucket[] buckets; // 时间轮桶
    private final DelayQueue<TimeWheelBucket> delayQueue; // 延迟队列

    private final ScheduledExecutorService executor; // 调度执行器
    private final AtomicBoolean running; // 运行状态

    private TimeWheel overflowWheel; // 溢出时间轮

    public TimeWheel(long tickMs, int wheelSize, long startTime) {
        this.tickMs = tickMs;
        this.wheelSize = wheelSize;
        this.interval = tickMs * wheelSize;
        this.startTime = startTime;
        this.currentTime = new AtomicLong(startTime - (startTime % tickMs));
        this.buckets = new TimeWheelBucket[wheelSize];
        this.delayQueue = new DelayQueue<>();
        this.executor = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "time-wheel-worker");
            t.setDaemon(true);
            return t;
        });
        this.running = new AtomicBoolean(false);

        // 初始化所有桶
        for (int i = 0; i < wheelSize; i++) {
            buckets[i] = new TimeWheelBucket();
        }
    }

    /**
     * 添加定时任务
     */
    public boolean addTask(TimerTask task) {
        long expiration = task.getDelayMs();
        long currentTimeMs = currentTime.get();

        if (expiration < currentTimeMs + tickMs) {
            // 任务已过期，立即执行
            return false;
        }

        if (expiration < currentTimeMs + interval) {
            // 在当前时间轮范围内
            long virtualId = (expiration / tickMs);
            int index = (int) (virtualId % wheelSize);
            TimeWheelBucket bucket = buckets[index];
            bucket.addTask(task);

            // 如果桶还没有在延迟队列中，则添加
            // 桶的过期时间应该是任务过期时间，而不是虚拟ID乘以tickMs
            if (bucket.setExpiration(expiration)) {
                delayQueue.offer(bucket);
            }
            return true;
        } else {
            // 需要溢出时间轮
            if (overflowWheel == null) {
                addOverflowWheel();
            }
            return overflowWheel.addTask(task);
        }
    }

    /**
     * 推进时间轮
     */
    public void advanceClock(long timeMs) {
        if (timeMs >= currentTime.get() + tickMs) {
            currentTime.set(timeMs - (timeMs % tickMs));

            // 推进溢出时间轮
            if (overflowWheel != null) {
                overflowWheel.advanceClock(timeMs);
            }
        }
    }

    /**
     * 启动时间轮
     */
    public void start() {
        if (running.compareAndSet(false, true)) {
            executor.scheduleWithFixedDelay(this::run, 0, tickMs, TimeUnit.MILLISECONDS);
        }
    }

    /**
     * 停止时间轮
     */
    public void stop() {
        if (running.compareAndSet(true, false)) {
            executor.shutdown();
            if (overflowWheel != null) {
                overflowWheel.stop();
            }
        }
    }

    /**
     * 运行时间轮
     */
    private void run() {
        try {
            // 推进当前时间
            long currentTimeMs = System.currentTimeMillis();
            advanceClock(currentTimeMs);

            // 处理所有到期的桶
            TimeWheelBucket bucket;
            while ((bucket = delayQueue.poll()) != null) {
                bucket.flush(task -> {
                    // 检查任务是否已过期，如果过期则直接执行，否则重新添加到时间轮
                    if (task.isExpired()) {
                        task.run();
                    } else {
                        addTask(task);
                    }
                });
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    /**
     * 添加溢出时间轮
     */
    private void addOverflowWheel() {
        synchronized (this) {
            if (overflowWheel == null) {
                overflowWheel = new TimeWheel(interval, wheelSize, currentTime.get());
            }
        }
    }

    /**
     * 获取当前时间
     */
    public long getCurrentTime() {
        return currentTime.get();
    }

    /**
     * 获取时间轮大小
     */
    public int getWheelSize() {
        return wheelSize;
    }

    /**
     * 获取时间间隔
     */
    public long getInterval() {
        return interval;
    }
} 
