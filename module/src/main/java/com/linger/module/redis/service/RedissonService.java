package com.linger.module.redis.service;

import com.linger.module.redis.model.DelayMessageRequest;
import com.linger.module.redis.model.DelayTaskMessage;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.*;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.concurrent.TimeUnit;

/**
 * @version 1.0
 * @description TaskGrabService
 * @date 2025/7/21 17:37:19
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class RedissonService {

    private final RedissonClient redissonClient;

    private static final String TASK_LIST_KEY = "tasks:available";
    private static final String USER_TASK_MAP = "tasks:assigned";


    private static final String QUEUE_NAME = "delay:msg";

    public String grabTask(String userId) {
        RLock lock = redissonClient.getLock("lock:grab:" + userId);

        try {
            if (lock.tryLock(1, 5, TimeUnit.SECONDS)) {
                // 使用 Redisson 的 List 模拟任务队列
                RList<String> taskList = redissonClient.getList(TASK_LIST_KEY);

                if (taskList.isEmpty()) {
                    return "任务已抢完";
                }

                String taskId = taskList.remove(0); // 并发安全弹出
                RMap<String, String> userTaskMap = redissonClient.getMap(USER_TASK_MAP);
                userTaskMap.put(userId, taskId);

                return "用户 " + userId + " 成功抢到任务 " + taskId;
            } else {
                return "系统繁忙，请稍后再试";
            }
        } catch (Exception e) {
            return "异常：" + e.getMessage();
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }

    public void sendMsg(DelayMessageRequest request) {
        RBlockingDeque<DelayTaskMessage> blockingDeque = redissonClient.getBlockingDeque(QUEUE_NAME);
        RDelayedQueue<DelayTaskMessage> delayedQueue = redissonClient.getDelayedQueue(blockingDeque);

        DelayTaskMessage message = new DelayTaskMessage(request.getId(), "DELIVERY");

        LocalDateTime dateTime = LocalDateTime.now();
        long timestamp = dateTime.toEpochSecond(ZoneOffset.of("+8"));
        log.info("发送消息：{},当前时间是 {},时间戳是{}", message, dateTime, timestamp);

        delayedQueue.offer(message, request.getDelaySecond(), TimeUnit.SECONDS);
    }

    @PostConstruct
    public void consumedMsg() {
        log.info("开始处理 延时消息");
        new Thread(() -> {
            RBlockingDeque<DelayTaskMessage> blockingDeque = redissonClient.getBlockingDeque(QUEUE_NAME);
            while (true) {
                try {
                    DelayTaskMessage task = blockingDeque.take(); // 阻塞直到有消息
                    log.info("处理延迟任务: id={}, type={}", task.getId(), task.getType());
                } catch (Exception e) {
                    log.error("处理延时消息异常", e);
                }
            }
        }, "delay-consumer").start();
    }


}
