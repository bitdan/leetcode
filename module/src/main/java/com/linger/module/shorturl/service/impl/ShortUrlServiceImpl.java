package com.linger.module.shorturl.service.impl;

import com.linger.module.shorturl.model.ShortUrlCreateRequest;
import com.linger.module.shorturl.model.ShortUrlCreateResponse;
import com.linger.module.shorturl.model.ShortUrlStats;
import com.linger.module.shorturl.service.ShortUrlService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RAtomicLong;
import org.redisson.api.RBucket;
import org.redisson.api.RMapCache;
import org.redisson.api.RedissonClient;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.net.URI;
import java.net.URISyntaxException;
import java.time.Instant;
import java.util.Locale;
import java.util.concurrent.TimeUnit;

/**
 * 基于 Redisson 的短链实现
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class ShortUrlServiceImpl implements ShortUrlService {

    private final RedissonClient redissonClient;

    private static final String ID_KEY = "short:url:id";
    private static final String URL_TO_CODE_MAP = "short:url:url2code";
    private static final String CODE_TO_URL_PREFIX = "short:url:code:";
    private static final String STATS_TOTAL_PREFIX = "short:url:stats:total:";
    private static final String STATS_LAST_PREFIX = "short:url:stats:last:";
    private static final String RATE_LIMIT_PREFIX = "short:url:ratelimit:create:";

    /**
     * 允许每个 IP 每分钟创建的最大短链数量
     */
    private static final long MAX_CREATE_PER_MINUTE = 60;

    @Override
    public ShortUrlCreateResponse createShortUrl(ShortUrlCreateRequest request, String clientIp) {
        validateRequest(request);
        checkRateLimit(clientIp);

        String longUrl = normalizeUrl(request.getLongUrl());
        boolean reuse = request.getReuse() == null || request.getReuse();
        Long expireSeconds = request.getExpireSeconds();

        long now = Instant.now().toEpochMilli();
        Long expireAt = (expireSeconds != null && expireSeconds > 0)
                ? now + expireSeconds * 1000
                : null;

        // 1. 复用已有短链
        if (reuse) {
            RMapCache<String, String> url2Code = redissonClient.getMapCache(URL_TO_CODE_MAP);
            String existingCode = url2Code.get(longUrl);
            if (StringUtils.hasText(existingCode)) {
                return new ShortUrlCreateResponse(existingCode, null, longUrl, expireAt);
            }
        }

        // 2. 生成新的短链 code（基于自增 ID + Base62）
        String code = generateCode();

        // 3. 存储 code -> longUrl
        RBucket<String> codeBucket = redissonClient.getBucket(CODE_TO_URL_PREFIX + code);
        if (expireSeconds != null && expireSeconds > 0) {
            codeBucket.set(longUrl, expireSeconds, TimeUnit.SECONDS);
        } else {
            codeBucket.set(longUrl);
        }

        // 4. 存储 longUrl -> code（用于复用）
        if (reuse) {
            RMapCache<String, String> url2Code = redissonClient.getMapCache(URL_TO_CODE_MAP);
            if (expireSeconds != null && expireSeconds > 0) {
                url2Code.put(longUrl, code, expireSeconds, TimeUnit.SECONDS);
            } else {
                url2Code.put(longUrl, code);
            }
        }

        return new ShortUrlCreateResponse(code, null, longUrl, expireAt);
    }

    @Override
    public String resolveLongUrl(String code) {
        if (!StringUtils.hasText(code)) {
            return null;
        }
        RBucket<String> bucket = redissonClient.getBucket(CODE_TO_URL_PREFIX + code);
        String longUrl = bucket.get();
        if (!StringUtils.hasText(longUrl)) {
            return null;
        }

        // 更新统计信息
        updateStats(code);
        return longUrl;
    }

    @Override
    public ShortUrlStats getStats(String code) {
        if (!StringUtils.hasText(code)) {
            return null;
        }
        RAtomicLong counter = redissonClient.getAtomicLong(STATS_TOTAL_PREFIX + code);
        long total = counter.isExists() ? counter.get() : 0;

        RBucket<Long> lastBucket = redissonClient.getBucket(STATS_LAST_PREFIX + code);
        Long last = lastBucket.get();
        return new ShortUrlStats(code, total, last);
    }

    private void validateRequest(ShortUrlCreateRequest request) {
        if (request == null || !StringUtils.hasText(request.getLongUrl())) {
            throw new IllegalArgumentException("长链不能为空");
        }
        try {
            new URI(request.getLongUrl());
        } catch (URISyntaxException e) {
            throw new IllegalArgumentException("长链不是合法的 URL", e);
        }
    }

    /**
     * 简单标准化 URL，避免大小写等导致无法复用
     */
    private String normalizeUrl(String url) {
        if (!StringUtils.hasText(url)) {
            return url;
        }
        // 去掉多余空格
        url = url.trim();
        // scheme 统一小写
        int idx = url.indexOf("://");
        if (idx > 0) {
            String scheme = url.substring(0, idx).toLowerCase(Locale.ROOT);
            String rest = url.substring(idx);
            return scheme + rest;
        }
        return url;
    }

    private String generateCode() {
        RAtomicLong idGenerator = redissonClient.getAtomicLong(ID_KEY);
        long id = idGenerator.incrementAndGet();
        return toBase62(id);
    }

    private void updateStats(String code) {
        RAtomicLong counter = redissonClient.getAtomicLong(STATS_TOTAL_PREFIX + code);
        counter.incrementAndGet();

        RBucket<Long> lastBucket = redissonClient.getBucket(STATS_LAST_PREFIX + code);
        lastBucket.set(Instant.now().toEpochMilli());
    }

    /**
     * 简单的 IP 维度限流：每分钟最多创建 N 条
     */
    private void checkRateLimit(String clientIp) {
        if (!StringUtils.hasText(clientIp)) {
            return;
        }
        long currentMinute = Instant.now().getEpochSecond() / 60;
        String key = RATE_LIMIT_PREFIX + clientIp + ":" + currentMinute;
        RAtomicLong counter = redissonClient.getAtomicLong(key);
        long count = counter.incrementAndGet();
        if (count == 1) {
            // 第一次访问时设置过期时间
            counter.expire(65, TimeUnit.SECONDS);
        }
        if (count > MAX_CREATE_PER_MINUTE) {
            throw new IllegalStateException("请求过于频繁，请稍后再试");
        }
    }

    private static final char[] BASE62 =
            "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz".toCharArray();

    private String toBase62(long value) {
        StringBuilder sb = new StringBuilder();
        while (value > 0) {
            int idx = (int) (value % 62);
            sb.append(BASE62[idx]);
            value = value / 62;
        }
        return sb.reverse().toString();
    }
}


