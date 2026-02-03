package com.linger.module.redisson.service;

import lombok.RequiredArgsConstructor;
import org.redisson.api.RScoredSortedSet;
import org.redisson.api.RedissonClient;
import org.springframework.stereotype.Service;

import java.util.AbstractMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 排行榜服务（基于 Redisson RScoredSortedSet）
 *
 * 适用百万级数据量：通过分页拉取，避免全量加载到内存。
 */
@Service
@RequiredArgsConstructor
public class RankingService {

    private static final String RANKING_KEY_PREFIX = "rank:";

    private final RedissonClient redissonClient;

    public void addScore(String board, String member, double delta) {
        getBoard(board).addScore(member, delta);
    }

    public void setScore(String board, String member, double score) {
        getBoard(board).add(score, member);
    }

    public Double getScore(String board, String member) {
        return getBoard(board).getScore(member);
    }

    /**
     * 获取 TopN（按分数从高到低）
     */
    public List<String> getTop(String board, int limit) {
        return getBoard(board).valueRangeReversed(0, Math.max(0, limit - 1))
                .stream()
                .collect(Collectors.toList());
    }

    /**
     * 获取 TopN（附带分数）
     */
    public List<Map.Entry<String, Double>> getTopWithScore(String board, int limit) {
        return getBoard(board).entryRangeReversed(0, Math.max(0, limit - 1))
                .stream()
                .map(e -> new AbstractMap.SimpleEntry<>(e.getValue(), e.getScore()))
                .collect(Collectors.toList());
    }

    /**
     * 获取排名（从 1 开始；不存在返回 null）
     */
    public Integer getRank(String board, String member) {
        Integer rank = getBoard(board).revRank(member);
        return rank == null ? null : rank + 1;
    }

    /**
     * 分页获取（按名次从高到低）
     *
     * @param startRank 从 1 开始
     * @param pageSize  每页大小
     */
    public List<Map.Entry<String, Double>> getPage(String board, int startRank, int pageSize) {
        int startIndex = Math.max(0, startRank - 1);
        int endIndex = startIndex + Math.max(0, pageSize - 1);
        return getBoard(board).entryRangeReversed(startIndex, endIndex)
                .stream()
                .map(e -> new AbstractMap.SimpleEntry<>(e.getValue(), e.getScore()))
                .collect(Collectors.toList());
    }

    public boolean remove(String board, String member) {
        return getBoard(board).remove(member);
    }

    public long size(String board) {
        return getBoard(board).size();
    }

    public void clear(String board) {
        getBoard(board).clear();
    }

    private RScoredSortedSet<String> getBoard(String board) {
        return redissonClient.getScoredSortedSet(RANKING_KEY_PREFIX + board);
    }
}
