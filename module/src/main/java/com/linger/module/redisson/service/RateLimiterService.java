package com.linger.module.redisson.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RRateLimiter;
import org.redisson.api.RateIntervalUnit;
import org.redisson.api.RateType;
import org.redisson.api.RedissonClient;
import org.springframework.stereotype.Service;

/**
 * Redisson 限流服务（基于 RRateLimiter）
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class RateLimiterService {

    private static final String LIMITER_KEY_PREFIX = "rate:limiter:";

    private final RedissonClient redissonClient;

    /**
     * 尝试获取许可（单次默认 1 个）
     */
    public boolean tryAcquire(String businessKey, long rate, long interval, RateIntervalUnit unit) {
        return tryAcquire(businessKey, 1, rate, interval, unit);
    }

    /**
     * 尝试获取指定数量许可
     */
    public boolean tryAcquire(String businessKey, long permits, long rate, long interval, RateIntervalUnit unit) {
        if (permits <= 0) {
            throw new IllegalArgumentException("permits must be positive");
        }

        RRateLimiter limiter = getLimiter(businessKey);
        limiter.trySetRate(RateType.OVERALL, rate, interval, unit);

        boolean acquired = permits == 1 ? limiter.tryAcquire() : limiter.tryAcquire(permits);
        if (!acquired) {
            log.debug("Rate limited for key={}, permits={}, rate={}/{} {}",
                    businessKey, permits, rate, interval, unit);
        }
        return acquired;
    }

    /**
     * 删除限流器配置（便于测试或重置）
     */
    public boolean reset(String businessKey) {
        return getLimiter(businessKey).delete();
    }

    private RRateLimiter getLimiter(String businessKey) {
        return redissonClient.getRateLimiter(LIMITER_KEY_PREFIX + businessKey);
    }
}
