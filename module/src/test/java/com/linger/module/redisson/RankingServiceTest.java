package com.linger.module.redisson;

import com.linger.module.redisson.service.RankingService;
import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.List;
import java.util.Map;
import java.util.stream.IntStream;

/**
 * 排行榜服务测试
 */
@SpringBootTest
@Slf4j
public class RankingServiceTest {

    @Autowired
    private RankingService rankingService;

    private String boardKey;

    @BeforeEach
    public void setUp() {
        boardKey = "board:test:" + System.currentTimeMillis();
        rankingService.clear(boardKey);
    }

    @Test
    public void testTopAndRank() {
        rankingService.setScore(boardKey, "u1", 10);
        rankingService.setScore(boardKey, "u2", 30);
        rankingService.setScore(boardKey, "u3", 20);

        List<String> top2 = rankingService.getTop(boardKey, 2);
        log.info("Top2: {}", top2);
        List<String> expected = new java.util.ArrayList<>();
        expected.add("u2");
        expected.add("u3");
        Assertions.assertEquals(expected, top2);

        Integer rankU2 = rankingService.getRank(boardKey, "u2");
        Integer rankU3 = rankingService.getRank(boardKey, "u3");
        Integer rankU1 = rankingService.getRank(boardKey, "u1");

        log.info("Ranks u2={}, u3={}, u1={}", rankU2, rankU3, rankU1);
        Assertions.assertEquals(1, rankU2);
        Assertions.assertEquals(2, rankU3);
        Assertions.assertEquals(3, rankU1);
    }

    @Test
    public void testPaging() {
        IntStream.rangeClosed(1, 50)
                .forEach(i -> rankingService.setScore(boardKey, "u" + i, i));

        List<Map.Entry<String, Double>> page = rankingService.getPage(boardKey, 1, 5);
        log.info("Page(1,5): {}", page);
        Assertions.assertEquals(5, page.size());
        Assertions.assertEquals("u50", page.get(0).getKey());
        Assertions.assertEquals("u46", page.get(4).getKey());
    }

    @Test
    public void testAddScore() {
        rankingService.setScore(boardKey, "u1", 5);
        rankingService.addScore(boardKey, "u1", 7);

        Double score = rankingService.getScore(boardKey, "u1");
        log.info("Score u1: {}", score);
        Assertions.assertEquals(12.0, score);
    }
}
