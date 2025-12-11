package com.linger.module.annotation;

import org.springframework.stereotype.Component;

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
}
