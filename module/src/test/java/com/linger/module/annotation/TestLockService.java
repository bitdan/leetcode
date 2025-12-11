package com.linger.module.annotation;


import org.springframework.stereotype.Component;

import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * @description TestLockService
 * @date 2025/12/11 18:30:31
 * @version 1.0
 */
@Component
public class TestLockService {
    private final AtomicInteger counter = new AtomicInteger(0);

    @RedisLock(key = "test:lock", interval = 2)
    public void doBusiness() {
        counter.incrementAndGet();
        try {
            Thread.sleep(200);
        } catch (InterruptedException ignored) {
        }
    }

    public int getCount() {
        return counter.get();
    }

    // 1. 固定key
    @RedisLock(key = "'test'", interval = 2)
    public void fixedKey() {
        // 业务逻辑
    }

    // 2. SpEL表达式 - 方法参数
    @RedisLock(key = "#id", prompt = "用户#{#id}正在处理中")
    public void withSpEL(Long id) {
        // 业务逻辑
    }

    // 3. SpEL表达式 - 集合参数
    @RedisLock(key = "#ids", prompt = "批量处理中")
    public void batchProcess(List<Long> ids) {
        // 业务逻辑，会为每个id创建锁
    }

    // 4. 复杂SpEL表达式
    @RedisLock(key = "'order:' + #order.id + ':update'", prompt = "订单#{#order.id}正在更新")
    public void updateOrder(Order order) {
        // 业务逻辑
    }

    // 5. 默认key（类名:方法名）
    @RedisLock(interval = 5)
    public void defaultKey() {
        // 业务逻辑
    }
}
