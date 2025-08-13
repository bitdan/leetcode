package com.linger.module.redisson;

import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.redisson.api.*;
import org.redisson.client.protocol.ScoredEntry;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.junit.jupiter.SpringJUnitConfig;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.AbstractMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

/**
 * @version 1.0
 * @description HotNewsRanking
 * @date 2024/8/19 12:55:06
 */

@Slf4j
@SpringBootTest
@SpringJUnitConfig
public class HotNewsRankingTest {

    @Autowired
    private RedissonClient redisson;

    private RScoredSortedSet<String> hotNews;
    private static final String HOT_NEWS_KEY = "hot_news_key";
    public static final Integer TOP_NEWS_COUNT = 10;

    @BeforeEach
    public void init() {
        // 确保redisson已注入
        if (redisson == null) {
            throw new IllegalStateException("RedissonClient is not injected");
        }

        // 初始化hotNews对象
        hotNews = redisson.getScoredSortedSet(HOT_NEWS_KEY);

        // 清除可能存在的旧数据
        clearRanking();
    }

    // 业务方法
    public void incrementNewsVisit(String newsId) {
        hotNews.addScore(newsId, 1);
    }

    public List<Map.Entry<String, Double>> getTopNews() {
        return hotNews.entryRangeReversed(0, TOP_NEWS_COUNT - 1)
                .stream()
                .map(entry -> new AbstractMap.SimpleEntry<>(entry.getValue(), entry.getScore()))
                .collect(Collectors.toList());
    }

    public List<String> getTopNewsId() {
        return hotNews.entryRangeReversed(0, TOP_NEWS_COUNT - 1)
                .stream()
                .map(ScoredEntry::getValue)
                .collect(Collectors.toList());
    }

    public void removeNews(String newsId) {
        hotNews.remove(newsId);
    }

    public void clearRanking() {
        hotNews.clear();
    }

    public long getTotalNewsCount() {
        return hotNews.size();
    }

    public Double getNewsScore(String newsId) {
        return hotNews.getScore(newsId);
    }

    // 测试方法
    @Test
    public void testNewsRanking() {
        // 使用正确初始化的实例
        for (int i = 0; i < 100; i++) {
            incrementNewsVisit("news1");
        }

        for (int i = 0; i < 150; i++) {
            incrementNewsVisit("news2");
        }

        for (int i = 0; i < 80; i++) {
            incrementNewsVisit("news3");
        }

        for (int i = 0; i < 200; i++) {
            incrementNewsVisit("news4");
        }

        for (int i = 0; i < 120; i++) {
            incrementNewsVisit("news5");
        }

        List<Map.Entry<String, Double>> topNews = getTopNews();
        log.info("topNews is : {}", topNews);
        List<String> topNewsId = getTopNewsId();
        log.info("topNewsId is : {}", topNewsId);
    }

    @Test
    public void testDelayQueue() throws InterruptedException {
        addTaskToDelayQueue("234");
        String order = getOrderFromDelayQueue();
        log.info("order is : {}", order);
    }

    public void addTaskToDelayQueue(String orderId) {
        RBlockingDeque<String> blockingDeque = redisson.getBlockingDeque("orderQueue");
        RDelayedQueue<String> delayedQueue = redisson.getDelayedQueue(blockingDeque);
        log.info("{}, add task ", LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
        delayedQueue.offer(orderId, 3, TimeUnit.SECONDS);
    }

    public String getOrderFromDelayQueue() throws InterruptedException {
        RBlockingDeque<String> blockingDeque = redisson.getBlockingDeque("orderQueue");
        return blockingDeque.take();
    }

    @Test
    public void testRateLimiterWithCompletableFuture() {
        RRateLimiter rateLimiter = redisson.getRateLimiter("myRateLimiter");
        rateLimiter.trySetRate(RateType.OVERALL, 3, 10, RateIntervalUnit.SECONDS);

        int allThreadNum = 20;
        long startTime = System.currentTimeMillis();

        List<CompletableFuture<Void>> futures = IntStream.range(0, allThreadNum)
                .mapToObj(i -> CompletableFuture.runAsync(() -> {
                    // 模拟部分线程延迟启动
                    if (i % 3 == 0) {
                        try {
                            Thread.sleep(1000);
                        } catch (InterruptedException e) {
                            throw new RuntimeException(e);
                        }
                    }

                    boolean pass = rateLimiter.tryAcquire();
                    if (pass) {
                        log.info("Thread {} acquired token", i);
                    } else {
                        log.info("Thread {} failed to acquire token", i);
                    }
                }))
                .collect(Collectors.toList());

        // 等待所有任务完成
        CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();

        log.info("Elapsed time: {} ms", (System.currentTimeMillis() - startTime));
    }
}
