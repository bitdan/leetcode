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
import java.util.Arrays;
import java.util.Collections;
import java.util.Objects;
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


    // Lua脚本内容
    private static final String PURCHASE_SCRIPT =
            "local userKey = KEYS[1]\n" +
                    "local limit = tonumber(ARGV[1])\n" +
                    "local expiry = tonumber(ARGV[2])\n" +
                    "\n" +
                    "local current = redis.call('GET', userKey)\n" +
                    "if current == false then\n" +
                    "    current = 0\n" +
                    "else\n" +
                    "    current = tonumber(current)\n" +
                    "end\n" +
                    "\n" +
                    "if current >= limit then\n" +
                    "    return 0\n" +
                    "end\n" +
                    "\n" +
                    "redis.call('INCR', userKey)\n" +
                    "if current == 0 then\n" +
                    "    redis.call('EXPIRE', userKey, expiry)\n" +
                    "end\n" +
                    "return 1";

    /**
     * 尝试购买商品 - Lua脚本原子操作
     *
     * @param userId        用户ID
     * @param productId     商品ID
     * @param purchaseLimit 用户限购数量
     * @param expirySeconds 过期时间（秒）
     * @return 是否购买成功
     */
    public boolean purchaseItem(Long userId, String productId, int purchaseLimit, int expirySeconds) {
        String key = getPurchaseKey(userId, productId);
        Long result = redissonClient.getScript().eval(
                RScript.Mode.READ_WRITE,
                PURCHASE_SCRIPT,
                RScript.ReturnType.INTEGER,
                Collections.singletonList(key),
                purchaseLimit, expirySeconds
        );
        return Objects.equals(result, 1L);
    }


    /**
     * 查询用户已购买数量
     */
    public long getUserPurchaseCount(Long userId, String productId) {
        String key = getPurchaseKey(userId, productId);
        return redissonClient.getAtomicLong(key).get();
    }

    /**
     * 重置用户购买记录（测试用）
     */
    public void resetUserPurchase(Long userId, String productId) {
        String key = getPurchaseKey(userId, productId);
        redissonClient.getBucket(key).delete();
    }

    private String getPurchaseKey(Long userId, String productId) {
        return String.format("live:user:%s:product:%s", userId, productId);
    }


    private static final String PURCHASE_SCRIPT_WITH_GLOBAL_LIMIT =
            "local userKey = KEYS[1]\n" +
                    "local globalKey = KEYS[2]\n" +
                    "local perUserLimit = tonumber(ARGV[1])\n" +
                    "local globalLimit = tonumber(ARGV[2])\n" +
                    "local expiry = tonumber(ARGV[3])\n" +
                    "\n" +
                    "local userCurrent = redis.call('GET', userKey) or '0'\n" +
                    "userCurrent = tonumber(userCurrent)\n" +
                    "\n" +
                    "local globalCurrent = redis.call('GET', globalKey) or '0'\n" +
                    "globalCurrent = tonumber(globalCurrent)\n" +
                    "\n" +
                    "if userCurrent >= perUserLimit or globalCurrent >= globalLimit then\n" +
                    "    return 0\n" +
                    "end\n" +
                    "\n" +
                    "redis.call('INCR', userKey)\n" +
                    "if userCurrent == 0 then\n" +
                    "    redis.call('EXPIRE', userKey, expiry)\n" +
                    "end\n" +
                    "\n" +
                    "redis.call('INCR', globalKey)\n" +
                    "if globalCurrent == 0 then\n" +
                    "    redis.call('EXPIRE', globalKey, expiry)\n" +
                    "end\n" +
                    "return 1";

    public boolean purchaseItem(Long userId, String productId,
                                int perUserLimit, int globalLimit,
                                int expirySeconds) {
        String userKey = "live:user:" + userId + ":product:" + productId;
        String globalKey = "live:product:" + productId + ":global";

        Long eval = redissonClient.getScript().eval(
                RScript.Mode.READ_WRITE,
                PURCHASE_SCRIPT_WITH_GLOBAL_LIMIT,
                RScript.ReturnType.INTEGER,
                Arrays.asList(userKey, globalKey),
                perUserLimit, globalLimit, expirySeconds
        );
        return Objects.equals(eval, 1L);
    }

    public long getGlobalSoldCount(String productId) {
        String key = "live:product:" + productId + ":global";
        return redissonClient.getAtomicLong(key).get();
    }

    public void resetGlobalSoldCount(String productId) {
        String key = "live:product:" + productId + ":global";
        redissonClient.getBucket(key).delete();
    }
}
