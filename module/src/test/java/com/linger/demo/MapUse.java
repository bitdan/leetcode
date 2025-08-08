package com.linger.demo;

import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;

import java.util.HashMap;

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
}
