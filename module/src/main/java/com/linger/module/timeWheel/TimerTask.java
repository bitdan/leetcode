package com.linger.module.timeWheel;

import java.util.concurrent.atomic.AtomicInteger;

/**
 * 定时任务
 */
public class TimerTask {

    private final long delayMs; // 延迟时间（毫秒）
    private final Runnable task; // 任务执行逻辑
    private final long createTime; // 创建时间
    private final int taskId; // 任务ID

    private static final AtomicInteger TASK_ID_GENERATOR = new AtomicInteger(0);

    public TimerTask(long delayMs, Runnable task) {
        this.delayMs = System.currentTimeMillis() + delayMs;
        this.task = task;
        this.createTime = System.currentTimeMillis();
        this.taskId = TASK_ID_GENERATOR.incrementAndGet();
    }

    /**
     * 获取延迟时间（毫秒）
     */
    public long getDelayMs() {
        return delayMs;
    }

    /**
     * 执行任务
     */
    public void run() {
        if (task != null) {
            try {
                task.run();
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    /**
     * 获取创建时间
     */
    public long getCreateTime() {
        return createTime;
    }

    /**
     * 获取任务ID
     */
    public int getTaskId() {
        return taskId;
    }

    /**
     * 检查任务是否已过期
     */
    public boolean isExpired() {
        return System.currentTimeMillis() >= delayMs;
    }

    @Override
    public String toString() {
        return "TimerTask{" +
                "taskId=" + taskId +
                ", delayMs=" + delayMs +
                ", createTime=" + createTime +
                '}';
    }
} 
