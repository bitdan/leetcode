package com.linger.module.groupbuy;

import com.linger.module.groupbuy.model.GroupTaskCreateRequest;
import com.linger.module.groupbuy.model.GroupTaskDetail;
import com.linger.module.groupbuy.model.GroupTaskStatus;
import com.linger.module.groupbuy.model.UserEligibilityProfile;
import com.linger.module.groupbuy.service.GroupTaskService;
import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.Arrays;
import java.util.HashSet;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 拼团任务服务测试
 */
@Slf4j
public class GroupTaskServiceTest {

    private final GroupTaskService groupTaskService = new GroupTaskService();

    @Test
    public void testClaimCompleteAndReachTargetCount() {
        GroupTaskCreateRequest request = buildBaseRequest();
        Long taskId = groupTaskService.publishTask(request);

        Instant now = Instant.parse("2026-02-13T10:00:00Z");
        assertTrue(groupTaskService.claimTask(taskId, buildUser(1001L, 3, "new", "verified"), now));
        assertTrue(groupTaskService.completeTask(taskId, 1001L, now.plusSeconds(30)));
        assertTrue(groupTaskService.claimTask(taskId, buildUser(1002L, 2, "new", "verified"), now.plusSeconds(40)));
        assertTrue(groupTaskService.completeTask(taskId, 1002L, now.plusSeconds(60)));

        GroupTaskDetail detail = groupTaskService.getTaskDetail(taskId);
        log.info("任务完成详情: {}", detail);
        assertEquals(2, detail.getCompletedCount());
        assertEquals(GroupTaskStatus.COMPLETED, detail.getStatus());
    }

    @Test
    public void testUserNotEligibleCannotClaim() {
        GroupTaskCreateRequest request = buildBaseRequest();
        Long taskId = groupTaskService.publishTask(request);

        Instant now = Instant.parse("2026-02-13T11:00:00Z");
        boolean claimed = groupTaskService.claimTask(taskId, buildUser(2001L, 1, "new"), now);
        log.info("不符合条件用户接单结果: taskId={}, claimed={}", taskId, claimed);
        assertFalse(claimed);
    }

    @Test
    public void testTimeoutCancelAndReassign() {
        GroupTaskCreateRequest request = buildBaseRequest();
        Long taskId = groupTaskService.publishTask(request);
        Instant base = Instant.parse("2026-02-13T12:00:00Z");

        assertTrue(groupTaskService.claimTask(taskId, buildUser(1001L, 3, "new", "verified"), base));
        assertTrue(groupTaskService.claimTask(taskId, buildUser(1002L, 2, "new", "verified"), base.plusSeconds(10)));

        int timeoutCount = groupTaskService.cancelExpiredClaims(base.plusSeconds(131));
        log.info("超时取消数量: {}", timeoutCount);
        assertEquals(2, timeoutCount);

        assertTrue(groupTaskService.claimTask(taskId, buildUser(1003L, 2, "new", "verified"), base.plusSeconds(132)));
        assertTrue(groupTaskService.completeTask(taskId, 1003L, base.plusSeconds(150)));
        assertTrue(groupTaskService.claimTask(taskId, buildUser(1004L, 4, "new", "verified"), base.plusSeconds(151)));
        assertTrue(groupTaskService.completeTask(taskId, 1004L, base.plusSeconds(170)));

        GroupTaskDetail detail = groupTaskService.getTaskDetail(taskId);
        log.info("补位完成后任务详情: {}", detail);
        assertEquals(2, detail.getCompletedCount());
        assertEquals(GroupTaskStatus.COMPLETED, detail.getStatus());
    }

    @Test
    public void testNoMoreClaimsAfterCompleted() {
        GroupTaskCreateRequest request = buildBaseRequest();
        Long taskId = groupTaskService.publishTask(request);
        Instant now = Instant.parse("2026-02-13T13:00:00Z");

        assertTrue(groupTaskService.claimTask(taskId, buildUser(1001L, 3, "new", "verified"), now));
        assertTrue(groupTaskService.completeTask(taskId, 1001L, now.plusSeconds(10)));
        assertTrue(groupTaskService.claimTask(taskId, buildUser(1002L, 2, "new", "verified"), now.plusSeconds(20)));
        assertTrue(groupTaskService.completeTask(taskId, 1002L, now.plusSeconds(30)));

        boolean thirdClaim = groupTaskService.claimTask(taskId, buildUser(1003L, 3, "new", "verified"), now.plusSeconds(40));
        log.info("成团后再接单结果: {}", thirdClaim);
        assertFalse(thirdClaim);
    }

    @Test
    public void testConcurrentClaimAndComplete() throws InterruptedException {
        int targetCompleteCount = 300;
        int concurrentUsers = 1000;
        int poolSize = 80;

        GroupTaskCreateRequest request = new GroupTaskCreateRequest();
        request.setPublisherId(8888L);
        request.setRequiredCompleteCount(targetCompleteCount);
        request.setClaimTimeoutSeconds(300L);
        Long taskId = groupTaskService.publishTask(request);

        ExecutorService executor = Executors.newFixedThreadPool(poolSize);
        CountDownLatch startLatch = new CountDownLatch(1);
        CountDownLatch doneLatch = new CountDownLatch(concurrentUsers);
        AtomicInteger claimSuccess = new AtomicInteger(0);
        AtomicInteger completeSuccess = new AtomicInteger(0);

        Instant base = Instant.parse("2026-02-13T14:00:00Z");
        long startNanos = System.nanoTime();
        for (int i = 0; i < concurrentUsers; i++) {
            final long userId = 100000L + i;
            executor.submit(() -> {
                try {
                    startLatch.await();
                    Instant now = base.plusMillis(userId % 30);
                    boolean claimed = groupTaskService.claimTask(taskId, buildUser(userId, 1, "new"), now);
                    if (claimed) {
                        claimSuccess.incrementAndGet();
                        boolean completed = groupTaskService.completeTask(taskId, userId, now.plusSeconds(1));
                        if (completed) {
                            completeSuccess.incrementAndGet();
                        }
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                } finally {
                    doneLatch.countDown();
                }
            });
        }

        startLatch.countDown();
        boolean finished = doneLatch.await(30, TimeUnit.SECONDS);
        executor.shutdownNow();

        assertTrue(finished, "并发测试任务应在超时时间内完成");
        GroupTaskDetail detail = groupTaskService.getTaskDetail(taskId);
        long elapsedMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startNanos);
        double qps = elapsedMs == 0 ? 0 : (double) concurrentUsers / elapsedMs * 1000;

        log.info("并发测试结果: concurrentUsers={}, targetCompleteCount={}, claimSuccess={}, completeSuccess={}, elapsedMs={}, approxQps={}",
                concurrentUsers, targetCompleteCount, claimSuccess.get(), completeSuccess.get(), elapsedMs, String.format("%.2f", qps));

        assertEquals(targetCompleteCount, completeSuccess.get(), "最终完成数应等于发布目标人数");
        assertEquals(targetCompleteCount, detail.getCompletedCount(), "任务完成数应与服务统计一致");
        assertEquals(GroupTaskStatus.COMPLETED, detail.getStatus(), "达到目标人数后应为已完成状态");
    }

    private GroupTaskCreateRequest buildBaseRequest() {
        GroupTaskCreateRequest request = new GroupTaskCreateRequest();
        request.setPublisherId(9999L);
        request.setRequiredCompleteCount(2);
        request.setClaimTimeoutSeconds(120L);
        request.setAllowedUserIds(new HashSet<>(Arrays.asList(1001L, 1002L, 1003L, 1004L)));
        request.setMinVipLevel(2);
        request.setRequiredTags(new HashSet<>(Arrays.asList("new", "verified")));
        return request;
    }

    private UserEligibilityProfile buildUser(Long userId, Integer vipLevel, String... tags) {
        return UserEligibilityProfile.builder()
                .userId(userId)
                .vipLevel(vipLevel)
                .tags(new HashSet<>(Arrays.asList(tags)))
                .build();
    }
}
