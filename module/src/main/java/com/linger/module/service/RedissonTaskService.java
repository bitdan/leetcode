package com.linger.module.service;

import lombok.RequiredArgsConstructor;
import org.redisson.api.RList;
import org.redisson.api.RLock;
import org.redisson.api.RMap;
import org.redisson.api.RedissonClient;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;

/**
 * @version 1.0
 * @description TaskGrabService
 * @date 2025/7/21 17:37:19
 */
@Service
@RequiredArgsConstructor
public class RedissonTaskService {

    private final RedissonClient redissonClient;

    private static final String TASK_LIST_KEY = "tasks:available";
    private static final String USER_TASK_MAP = "tasks:assigned";

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

}
