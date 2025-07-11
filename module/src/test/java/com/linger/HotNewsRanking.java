package com.linger;

import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;
import org.redisson.Redisson;
import org.redisson.api.*;
import org.redisson.client.codec.StringCodec;
import org.redisson.config.Config;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.AbstractMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/**
 * @version 1.0
 * @description HotNewsRanking
 * @date 2024/8/19 12:55:06
 */
@Slf4j
public class HotNewsRanking {
    private static final String HOT_NEWS_KEY = "hot_news_key";
    public static final Integer TOP_NEWS_COUNT = 10;
    private final RedissonClient redisson;
    private final RScoredSortedSet<String> hotNews;


    public HotNewsRanking() {
        Config config = new Config();
        config.setCodec(new StringCodec());
        config.useSingleServer()
            .setDatabase(15)
            .setPassword("dudu0.0@")
            .setAddress("redis://139.159.140.112:30379");
        this.redisson = Redisson.create(config);
        this.hotNews = redisson.getScoredSortedSet(HOT_NEWS_KEY);
    }

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
            .map(entry -> entry.getValue())
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

    public void close() {
        redisson.shutdown();
    }

    @Test
    public void test() {
        HotNewsRanking ranking = new HotNewsRanking();
        ranking.clearRanking();
        for (int i = 0; i < 100; i++) {
            ranking.incrementNewsVisit("news1");
        }

        for (int i = 0; i < 150; i++) {
            ranking.incrementNewsVisit("news2");
        }

        for (int i = 0; i < 80; i++) {
            ranking.incrementNewsVisit("news3");
        }

        for (int i = 0; i < 200; i++) {
            ranking.incrementNewsVisit("news4");
        }

        for (int i = 0; i < 120; i++) {
            ranking.incrementNewsVisit("news5");
        }

        List<Map.Entry<String, Double>> topNews = ranking.getTopNews();
        log.info("topNews is : {}", topNews);
        List<String> topNewsId = ranking.getTopNewsId();
        log.info("topNewsId is : {}", topNewsId);
        ranking.close();
    }

    @Test
    public void test1() throws InterruptedException {
        addTaskToDelayQueue("234");
        for (int i = 0; i < 2; i++) {
            String order = getOrderFromDelayQueue();
            log.info("order is : {}", order);
        }

    }


    public void addTaskToDelayQueue(String orderId) {

        RBlockingDeque<String> blockingDeque = redisson.getBlockingDeque("orderQueue");
        RDelayedQueue<String> delayedQueue = redisson.getDelayedQueue(blockingDeque);
        log.info("{}, add task ", LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
        delayedQueue.offer(orderId, 3, TimeUnit.SECONDS);
        delayedQueue.offer(orderId, 6, TimeUnit.SECONDS);
        delayedQueue.offer(orderId, 9, TimeUnit.SECONDS);
    }

    public String getOrderFromDelayQueue() throws InterruptedException {
        RBlockingDeque<String> blockingDeque = redisson.getBlockingDeque("orderQueue");
        RDelayedQueue<String> delayedQueue = redisson.getDelayedQueue(blockingDeque);
        String orderId = blockingDeque.take();
        return orderId;
    }

    public RRateLimiter createLimiter() {
        RRateLimiter rateLimiter = redisson.getRateLimiter("myRateLimiter3");
        // 初始化：PER_CLIENT 单实例执行，OVERALL 全实例执行
        // 最大流速 = 每10秒钟产生3个令牌
        rateLimiter.trySetRate(RateType.OVERALL, 3, 10, RateIntervalUnit.SECONDS);
        return rateLimiter;
    }


    @Test
    public void test2() throws InterruptedException {
        RRateLimiter rateLimiter = createLimiter();
        int allThreadNum = 20;
        CountDownLatch latch = new CountDownLatch(allThreadNum);
        long startTime = System.currentTimeMillis();
        for (int i = 0; i < allThreadNum; i++) {
            int finalI = i;
            new Thread(() -> {
                if (finalI % 3 == 0) {
                    try {
                        Thread.sleep(1000);
                    } catch (InterruptedException e) {
                        throw new RuntimeException(e);
                    }
                }
                boolean pass = rateLimiter.tryAcquire();
                if (pass) {
                    log.info("get ");
                } else {
                    log.info("no");
                }
                latch.countDown();
            }).start();
        }
        latch.await();
        System.out.println("Elapsed " + (System.currentTimeMillis() - startTime));

    }

}
