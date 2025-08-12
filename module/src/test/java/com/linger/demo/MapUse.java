package com.linger.demo;

import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;

/**
 * @version 1.0
 * @description MapUse
 * @date 2025/8/8 14:49:01
 */
@Slf4j
public class MapUse {

    @Test
    public void testDateValidation1() {
        HashMap<String, String> map = new HashMap<>();
        map.computeIfAbsent("date", k -> new StringBuilder("2025-08-08").toString());
        map.computeIfPresent("date", (k, v) -> new StringBuilder(v).append(" 14:30:00").toString());

        log.info("map is : {}", map);
    }

    @Test
    public void testDateValidation2() throws ExecutionException, InterruptedException {
        CompletableFuture future = new CompletableFuture();
        future.thenApply(result -> {
            System.out.println(1 / 0);
            return 0;
        }).exceptionally(err -> {
            System.out.println("+ err.getMessage());System.out");
            return 0;
        });
        System.out.println(future.get());
    }
}
