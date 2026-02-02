package com.linger.module.redisson;

import com.linger.module.redisson.service.LikeService;
import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 朋友圈点赞功能测试类
 *
 * @version 1.0
 * @description 点赞服务测试
 * @date 2025/1/21
 */
@SpringBootTest
@Slf4j
public class LikeServiceTest {

    @Autowired
    private LikeService likeService;

    private Long testMomentId;
    private Long testUserId1;
    private Long testUserId2;
    private Long testUserId3;

    @BeforeEach
    public void setUp() {
        // 使用时间戳作为动态ID，避免测试数据冲突
        long timestamp = System.currentTimeMillis();
        testMomentId = timestamp;
        // 使用固定的用户ID，便于区分
        testUserId1 = 1001L;
        testUserId2 = 1002L;
        testUserId3 = 1003L;

        // 清理测试用户的数据，避免不同测试用例之间的数据干扰
        likeService.clearUserLikes(testUserId1);
        likeService.clearUserLikes(testUserId2);
        likeService.clearUserLikes(testUserId3);

        log.info("=== 测试初始化 ===");
        log.info("测试动态ID: {}", testMomentId);
        log.info("测试用户ID: {}, {}, {}", testUserId1, testUserId2, testUserId3);
    }

    @Test
    public void testLike() {
        log.info("\n=== 测试1: 点赞功能 ===");

        // 1. 首次点赞应该成功
        boolean result1 = likeService.like(testMomentId, testUserId1);
        assertTrue(result1, "首次点赞应该成功");
        log.info("用户{}点赞动态{}: {}", testUserId1, testMomentId, result1 ? "成功" : "失败");

        // 2. 重复点赞应该失败
        boolean result2 = likeService.like(testMomentId, testUserId1);
        assertFalse(result2, "重复点赞应该失败");
        log.info("用户{}重复点赞动态{}: {}", testUserId1, testMomentId, result2 ? "成功" : "失败（预期）");

        // 3. 其他用户点赞应该成功
        boolean result3 = likeService.like(testMomentId, testUserId2);
        assertTrue(result3, "其他用户点赞应该成功");
        log.info("用户{}点赞动态{}: {}", testUserId2, testMomentId, result3 ? "成功" : "失败");
    }

    @Test
    public void testUnlike() {
        log.info("\n=== 测试2: 取消点赞功能 ===");

        // 1. 先点赞
        likeService.like(testMomentId, testUserId1);
        log.info("用户{}先点赞动态{}", testUserId1, testMomentId);

        // 2. 取消点赞应该成功
        boolean result1 = likeService.unlike(testMomentId, testUserId1);
        assertTrue(result1, "取消点赞应该成功");
        log.info("用户{}取消点赞动态{}: {}", testUserId1, testMomentId, result1 ? "成功" : "失败");

        // 3. 再次取消点赞应该失败
        boolean result2 = likeService.unlike(testMomentId, testUserId1);
        assertFalse(result2, "未点赞状态下取消点赞应该失败");
        log.info("用户{}再次取消点赞动态{}: {}", testUserId1, testMomentId, result2 ? "成功" : "失败（预期）");
    }

    @Test
    public void testToggleLike() {
        log.info("\n=== 测试3: 切换点赞状态功能 ===");

        // 1. 首次切换（未点赞 -> 点赞）
        boolean result1 = likeService.toggleLike(testMomentId, testUserId1);
        assertTrue(result1, "切换后应该是点赞状态");
        log.info("用户{}切换点赞状态（未点赞->点赞）: {}", testUserId1, result1 ? "已点赞" : "未点赞");

        // 2. 再次切换（点赞 -> 取消点赞）
        boolean result2 = likeService.toggleLike(testMomentId, testUserId1);
        assertFalse(result2, "切换后应该是未点赞状态");
        log.info("用户{}切换点赞状态（点赞->取消）: {}", testUserId1, result2 ? "已点赞" : "未点赞");

        // 3. 第三次切换（未点赞 -> 点赞）
        boolean result3 = likeService.toggleLike(testMomentId, testUserId1);
        assertTrue(result3, "切换后应该是点赞状态");
        log.info("用户{}切换点赞状态（未点赞->点赞）: {}", testUserId1, result3 ? "已点赞" : "未点赞");
    }

    @Test
    public void testIsLiked() {
        log.info("\n=== 测试4: 查询点赞状态功能 ===");

        // 1. 未点赞时查询
        boolean result1 = likeService.isLiked(testMomentId, testUserId1);
        assertFalse(result1, "未点赞时应该返回false");
        log.info("用户{}是否点赞动态{}: {}", testUserId1, testMomentId, result1);

        // 2. 点赞后查询
        likeService.like(testMomentId, testUserId1);
        boolean result2 = likeService.isLiked(testMomentId, testUserId1);
        assertTrue(result2, "点赞后应该返回true");
        log.info("用户{}是否点赞动态{}: {}", testUserId1, testMomentId, result2);

        // 3. 取消点赞后查询
        likeService.unlike(testMomentId, testUserId1);
        boolean result3 = likeService.isLiked(testMomentId, testUserId1);
        assertFalse(result3, "取消点赞后应该返回false");
        log.info("用户{}是否点赞动态{}: {}", testUserId1, testMomentId, result3);
    }

    @Test
    public void testGetLikeCount() {
        log.info("\n=== 测试5: 查询点赞数量功能 ===");

        // 1. 初始点赞数量应该为0
        long count1 = likeService.getLikeCount(testMomentId);
        assertEquals(0, count1, "初始点赞数量应该为0");
        log.info("动态{}的点赞数量: {}", testMomentId, count1);

        // 2. 点赞后数量增加
        likeService.like(testMomentId, testUserId1);
        long count2 = likeService.getLikeCount(testMomentId);
        assertEquals(1, count2, "点赞后数量应该为1");
        log.info("动态{}的点赞数量: {}", testMomentId, count2);

        // 3. 多个用户点赞
        likeService.like(testMomentId, testUserId2);
        likeService.like(testMomentId, testUserId3);
        long count3 = likeService.getLikeCount(testMomentId);
        assertEquals(3, count3, "三个用户点赞后数量应该为3");
        log.info("动态{}的点赞数量: {}", testMomentId, count3);

        // 4. 取消点赞后数量减少
        likeService.unlike(testMomentId, testUserId1);
        long count4 = likeService.getLikeCount(testMomentId);
        assertEquals(2, count4, "取消一个点赞后数量应该为2");
        log.info("动态{}的点赞数量: {}", testMomentId, count4);
    }

    @Test
    public void testGetLikeUsers() {
        log.info("\n=== 测试6: 查询点赞用户列表功能 ===");

        // 1. 初始应该为空
        Set<Long> users1 = likeService.getLikeUsers(testMomentId);
        assertTrue(users1.isEmpty(), "初始点赞用户列表应该为空");
        log.info("动态{}的点赞用户列表: {}", testMomentId, users1);

        // 2. 点赞后应该包含用户
        likeService.like(testMomentId, testUserId1);
        likeService.like(testMomentId, testUserId2);
        Set<Long> users2 = likeService.getLikeUsers(testMomentId);
        assertEquals(2, users2.size(), "点赞用户列表应该包含2个用户");
        assertTrue(users2.contains(testUserId1), "应该包含用户1");
        assertTrue(users2.contains(testUserId2), "应该包含用户2");
        log.info("动态{}的点赞用户列表: {}", testMomentId, users2);

        // 3. 取消点赞后应该移除用户
        likeService.unlike(testMomentId, testUserId1);
        Set<Long> users3 = likeService.getLikeUsers(testMomentId);
        assertEquals(1, users3.size(), "取消点赞后应该只剩1个用户");
        assertFalse(users3.contains(testUserId1), "不应该包含用户1");
        assertTrue(users3.contains(testUserId2), "应该包含用户2");
        log.info("动态{}的点赞用户列表: {}", testMomentId, users3);
    }

    @Test
    public void testGetUserLikedMoments() {
        log.info("\n=== 测试7: 查询用户点赞的动态列表功能 ===");

        Long momentId2 = testMomentId + 100;
        Long momentId3 = testMomentId + 200;

        // 1. 初始应该为空
        Set<Long> moments1 = likeService.getUserLikedMoments(testUserId1);
        assertTrue(moments1.isEmpty(), "初始用户点赞列表应该为空");
        log.info("用户{}点赞的动态列表: {}", testUserId1, moments1);

        // 2. 点赞多个动态后应该包含这些动态
        likeService.like(testMomentId, testUserId1);
        likeService.like(momentId2, testUserId1);
        likeService.like(momentId3, testUserId1);
        Set<Long> moments2 = likeService.getUserLikedMoments(testUserId1);
        assertEquals(3, moments2.size(), "用户点赞列表应该包含3个动态");
        assertTrue(moments2.contains(testMomentId), "应该包含动态1");
        assertTrue(moments2.contains(momentId2), "应该包含动态2");
        assertTrue(moments2.contains(momentId3), "应该包含动态3");
        log.info("用户{}点赞的动态列表: {}", testUserId1, moments2);

        // 3. 取消点赞后应该移除动态
        likeService.unlike(testMomentId, testUserId1);
        Set<Long> moments3 = likeService.getUserLikedMoments(testUserId1);
        assertEquals(2, moments3.size(), "取消点赞后应该只剩2个动态");
        assertFalse(moments3.contains(testMomentId), "不应该包含动态1");
        assertTrue(moments3.contains(momentId2), "应该包含动态2");
        assertTrue(moments3.contains(momentId3), "应该包含动态3");
        log.info("用户{}点赞的动态列表: {}", testUserId1, moments3);
    }

    @Test
    public void testBatchCheckLiked() {
        log.info("\n=== 测试8: 批量查询点赞状态功能 ===");

        Long momentId2 = testMomentId + 100;
        Long momentId3 = testMomentId + 200;

        // 1. 点赞部分动态
        likeService.like(testMomentId, testUserId1);
        likeService.like(momentId2, testUserId1);
        // momentId3 不点赞

        // 2. 批量查询
        Set<Long> momentIds = new HashSet<>();
        momentIds.add(testMomentId);
        momentIds.add(momentId2);
        momentIds.add(momentId3);
        Set<Long> likedMoments = likeService.batchCheckLiked(momentIds, testUserId1);

        assertEquals(2, likedMoments.size(), "应该返回2个已点赞的动态");
        assertTrue(likedMoments.contains(testMomentId), "应该包含动态1");
        assertTrue(likedMoments.contains(momentId2), "应该包含动态2");
        assertFalse(likedMoments.contains(momentId3), "不应该包含动态3");
        log.info("用户{}在动态列表{}中已点赞的动态: {}", testUserId1, momentIds, likedMoments);
    }

    @Test
    public void testDeleteAllLikes() {
        log.info("\n=== 测试9: 删除所有点赞记录功能 ===");

        // 1. 多个用户点赞
        likeService.like(testMomentId, testUserId1);
        likeService.like(testMomentId, testUserId2);
        likeService.like(testMomentId, testUserId3);
        long count1 = likeService.getLikeCount(testMomentId);
        assertEquals(3, count1, "应该有3个点赞");
        log.info("删除前，动态{}的点赞数量: {}", testMomentId, count1);

        // 2. 删除所有点赞
        likeService.deleteAllLikes(testMomentId);
        long count2 = likeService.getLikeCount(testMomentId);
        assertEquals(0, count2, "删除后点赞数量应该为0");
        log.info("删除后，动态{}的点赞数量: {}", testMomentId, count2);

        // 3. 验证用户的点赞列表也被清理
        Set<Long> user1Moments = likeService.getUserLikedMoments(testUserId1);
        assertFalse(user1Moments.contains(testMomentId), "用户1的点赞列表不应该包含该动态");
        Set<Long> user2Moments = likeService.getUserLikedMoments(testUserId2);
        assertFalse(user2Moments.contains(testMomentId), "用户2的点赞列表不应该包含该动态");
        Set<Long> user3Moments = likeService.getUserLikedMoments(testUserId3);
        assertFalse(user3Moments.contains(testMomentId), "用户3的点赞列表不应该包含该动态");
        log.info("验证完成：所有用户的点赞列表都已清理");
    }

    @Test
    public void testConcurrentLike() {
        log.info("\n=== 测试10: 并发点赞测试 ===");

        // 模拟多个用户同时点赞
        int threadCount = 10;
        Thread[] threads = new Thread[threadCount];
        Long[] userIds = new Long[threadCount];

        for (int i = 0; i < threadCount; i++) {
            userIds[i] = 1001L + i;  // 使用1001, 1002, 1003...格式
            final int index = i;
            threads[i] = new Thread(() -> {
                boolean result = likeService.like(testMomentId, userIds[index]);
                log.info("线程{}: 用户{}点赞动态{}: {}", index, userIds[index], testMomentId, result ? "成功" : "失败");
            });
        }

        // 启动所有线程
        for (Thread thread : threads) {
            thread.start();
        }

        // 等待所有线程完成
        for (Thread thread : threads) {
            try {
                thread.join();
            } catch (InterruptedException e) {
                log.error("线程等待异常", e);
            }
        }

        // 验证结果
        long finalCount = likeService.getLikeCount(testMomentId);
        assertEquals(threadCount, finalCount, "并发点赞后应该有" + threadCount + "个点赞");
        log.info("并发测试完成，最终点赞数量: {}", finalCount);
    }

    @Test
    public void testCompleteScenario() {
        log.info("\n=== 测试11: 完整场景测试 ===");

        Long momentId2 = testMomentId + 100;

        // 场景：用户1和用户2都点赞了动态1，用户1还点赞了动态2
        likeService.like(testMomentId, testUserId1);
        likeService.like(testMomentId, testUserId2);
        likeService.like(momentId2, testUserId1);

        // 验证动态1的点赞情况
        long count1 = likeService.getLikeCount(testMomentId);
        assertEquals(2, count1, "动态1应该有2个点赞");
        Set<Long> users1 = likeService.getLikeUsers(testMomentId);
        assertEquals(2, users1.size(), "动态1应该有2个点赞用户");
        log.info("动态{}: 点赞数量={}, 点赞用户={}", testMomentId, count1, users1);

        // 验证动态2的点赞情况
        long count2 = likeService.getLikeCount(momentId2);
        assertEquals(1, count2, "动态2应该有1个点赞");
        Set<Long> users2 = likeService.getLikeUsers(momentId2);
        assertEquals(1, users2.size(), "动态2应该有1个点赞用户");
        log.info("动态{}: 点赞数量={}, 点赞用户={}", momentId2, count2, users2);

        // 验证用户1的点赞列表
        Set<Long> user1Moments = likeService.getUserLikedMoments(testUserId1);
        assertEquals(2, user1Moments.size(), "用户1应该点赞了2个动态");
        assertTrue(user1Moments.contains(testMomentId), "用户1应该点赞了动态1");
        assertTrue(user1Moments.contains(momentId2), "用户1应该点赞了动态2");
        log.info("用户{}点赞的动态列表: {}", testUserId1, user1Moments);

        // 验证用户2的点赞列表
        Set<Long> user2Moments = likeService.getUserLikedMoments(testUserId2);
        assertEquals(1, user2Moments.size(), "用户2应该点赞了1个动态");
        assertTrue(user2Moments.contains(testMomentId), "用户2应该点赞了动态1");
        log.info("用户{}点赞的动态列表: {}", testUserId2, user2Moments);

        // 用户1取消对动态1的点赞
        likeService.unlike(testMomentId, testUserId1);

        // 再次验证
        long count1After = likeService.getLikeCount(testMomentId);
        assertEquals(1, count1After, "动态1应该只剩1个点赞");
        Set<Long> user1MomentsAfter = likeService.getUserLikedMoments(testUserId1);
        assertEquals(1, user1MomentsAfter.size(), "用户1应该只剩1个点赞");
        assertFalse(user1MomentsAfter.contains(testMomentId), "用户1不应该再点赞动态1");
        log.info("用户1取消点赞后，动态1点赞数量: {}, 用户1点赞列表: {}", count1After, user1MomentsAfter);

        log.info("完整场景测试完成");
    }
}

