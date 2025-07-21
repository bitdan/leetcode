package com.linger.module;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

/**
 * @version 1.0
 * @description ConcurrentGrabTest
 * @date 2025/7/21 17:41:52
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class RedissonConcurrentTest {

    private final String url = "http://localhost:9999/api/grabTask";

    @Test
    public void testConcurrentGrabWithCompletableFuture() {
        int threadCount = 30;

        List<CompletableFuture<Void>> futures = IntStream.range(0, threadCount)
                .mapToObj(i -> CompletableFuture.runAsync(() -> {
                    try {
                        String userId = "user" + i;
                        String fullUrl = url + "?userId=" + userId;

                        HttpURLConnection conn = (HttpURLConnection) new URL(fullUrl).openConnection();
                        conn.setRequestMethod("GET");
                        conn.setDoOutput(true);

                        int responseCode = conn.getResponseCode();
                        String body = new BufferedReader(new InputStreamReader(conn.getInputStream()))
                                .lines().collect(Collectors.joining("\n"));

                        System.out.println("用户 " + userId + " => 响应码: " + responseCode + "，内容: " + body);
                    } catch (Exception e) {
                        System.err.println("用户 user" + i + " 请求异常：" + e.getMessage());
                    }
                })).collect(Collectors.toList());

        // 等待所有并发任务完成
        CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();
    }
}

