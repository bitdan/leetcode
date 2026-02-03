package com.linger.module.redisson;

import com.linger.module.redisson.service.RateLimiterService;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.redisson.api.RateIntervalUnit;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * Redisson 限流器测试
 */
@SpringBootTest
public class RateLimiterServiceTest {

    @Autowired
    private RateLimiterService rateLimiterService;

    private String limiterKey;

    @BeforeEach
    public void setUp() {
        limiterKey = "rate:test:" + System.currentTimeMillis();
        rateLimiterService.reset(limiterKey);
    }

//    @AfterEach
//    public void tearDown() {
//        rateLimiterService.reset(limiterKey);
//    }

    @Test
    public void testSimpleRateLimit() throws InterruptedException {
        long rate = 2;
        long interval = 2;

        Assertions.assertTrue(rateLimiterService.tryAcquire(limiterKey, rate, interval, RateIntervalUnit.SECONDS));
        Assertions.assertTrue(rateLimiterService.tryAcquire(limiterKey, rate, interval, RateIntervalUnit.SECONDS));
        Assertions.assertFalse(rateLimiterService.tryAcquire(limiterKey, rate, interval, RateIntervalUnit.SECONDS));

        Thread.sleep(2100);
        Assertions.assertTrue(rateLimiterService.tryAcquire(limiterKey, rate, interval, RateIntervalUnit.SECONDS));
    }

    @Test
    public void testAcquireMultiplePermits() {
        long rate = 5;
        long interval = 10;

        Assertions.assertTrue(rateLimiterService.tryAcquire(limiterKey, 3, rate, interval, RateIntervalUnit.SECONDS));
        Assertions.assertTrue(rateLimiterService.tryAcquire(limiterKey, 2, rate, interval, RateIntervalUnit.SECONDS));
        Assertions.assertFalse(rateLimiterService.tryAcquire(limiterKey, 1, rate, interval, RateIntervalUnit.SECONDS));
    }
}
