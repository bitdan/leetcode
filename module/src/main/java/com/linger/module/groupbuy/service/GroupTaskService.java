package com.linger.module.groupbuy.service;

import com.linger.module.groupbuy.model.GroupTaskCreateRequest;
import com.linger.module.groupbuy.model.GroupTaskDetail;
import com.linger.module.groupbuy.model.GroupTaskStatus;
import com.linger.module.groupbuy.model.UserEligibilityProfile;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.time.Instant;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 拼团任务服务
 *
 * 规则：
 * 1. 任务发布时配置总完成人数与参与条件。
 * 2. 参与者接任务后必须在时限内完成，否则超时取消并释放名额。
 * 3. 最终只有达到发布时配置的完成人数，任务才算成团完成。
 */
@Service
@Slf4j
public class GroupTaskService {

    private final AtomicLong taskIdGenerator = new AtomicLong(0);
    private final Map<Long, TaskAggregate> taskStore = new ConcurrentHashMap<>();

    public Long publishTask(GroupTaskCreateRequest request) {
        validatePublishRequest(request);
        long taskId = taskIdGenerator.incrementAndGet();

        TaskAggregate aggregate = new TaskAggregate();
        aggregate.setTaskId(taskId);
        aggregate.setPublisherId(request.getPublisherId());
        aggregate.setRequiredCompleteCount(request.getRequiredCompleteCount());
        aggregate.setClaimTimeoutSeconds(request.getClaimTimeoutSeconds());
        aggregate.setAllowedUserIds(toMutableSet(request.getAllowedUserIds()));
        aggregate.setMinVipLevel(request.getMinVipLevel());
        aggregate.setRequiredTags(toMutableSet(request.getRequiredTags()));
        aggregate.setStatus(GroupTaskStatus.OPEN);

        taskStore.put(taskId, aggregate);
        log.info("发布拼团任务成功, taskId={}, requiredCompleteCount={}", taskId, request.getRequiredCompleteCount());
        return taskId;
    }

    public synchronized boolean claimTask(Long taskId, UserEligibilityProfile profile) {
        return claimTask(taskId, profile, Instant.now());
    }

    public synchronized boolean claimTask(Long taskId, UserEligibilityProfile profile, Instant now) {
        TaskAggregate task = requireTask(taskId);
        validateProfile(profile);
        cleanExpiredClaims(task, now);

        if (task.getStatus() == GroupTaskStatus.COMPLETED) {
            log.info("任务已成团完成，禁止继续接单, taskId={}", taskId);
            return false;
        }

        if (!matchesEligibility(task, profile)) {
            log.info("用户不满足接单条件, taskId={}, userId={}", taskId, profile.getUserId());
            return false;
        }

        if (task.getCompletedUserIds().contains(profile.getUserId())
                || task.getClaimingUsers().containsKey(profile.getUserId())) {
            log.info("用户已参与该任务, taskId={}, userId={}", taskId, profile.getUserId());
            return false;
        }

        int leftSlots = task.getRequiredCompleteCount() - task.getCompletedUserIds().size() - task.getClaimingUsers().size();
        if (leftSlots <= 0) {
            log.info("当前无可分配名额, taskId={}", taskId);
            return false;
        }

        ClaimContext claim = new ClaimContext();
        claim.setClaimTime(now);
        claim.setDeadline(now.plusSeconds(task.getClaimTimeoutSeconds()));
        task.getClaimingUsers().put(profile.getUserId(), claim);

        log.info("接单成功, taskId={}, userId={}, deadline={}", taskId, profile.getUserId(), claim.getDeadline());
        return true;
    }

    public synchronized boolean completeTask(Long taskId, Long userId) {
        return completeTask(taskId, userId, Instant.now());
    }

    public synchronized boolean completeTask(Long taskId, Long userId, Instant now) {
        TaskAggregate task = requireTask(taskId);
        cleanExpiredClaims(task, now);

        ClaimContext claim = task.getClaimingUsers().get(userId);
        if (claim == null) {
            log.info("用户未处于接单中，无法完成任务, taskId={}, userId={}", taskId, userId);
            return false;
        }

        if (now.isAfter(claim.getDeadline())) {
            task.getClaimingUsers().remove(userId);
            log.info("用户超时未完成，任务已回收, taskId={}, userId={}", taskId, userId);
            return false;
        }

        task.getClaimingUsers().remove(userId);
        task.getCompletedUserIds().add(userId);

        if (task.getCompletedUserIds().size() >= task.getRequiredCompleteCount()) {
            task.setStatus(GroupTaskStatus.COMPLETED);
            log.info("拼团任务达成, taskId={}, completedCount={}", taskId, task.getCompletedUserIds().size());
        } else {
            log.info("用户完成任务, taskId={}, userId={}, completedCount={}",
                    taskId, userId, task.getCompletedUserIds().size());
        }
        return true;
    }

    public synchronized int cancelExpiredClaims(Instant now) {
        int total = 0;
        for (TaskAggregate task : taskStore.values()) {
            total += cleanExpiredClaims(task, now);
        }
        return total;
    }

    public GroupTaskDetail getTaskDetail(Long taskId) {
        TaskAggregate task = requireTask(taskId);
        return new GroupTaskDetail(
                task.getTaskId(),
                task.getPublisherId(),
                task.getRequiredCompleteCount(),
                task.getCompletedUserIds().size(),
                task.getClaimingUsers().size(),
                task.getClaimTimeoutSeconds(),
                task.getStatus());
    }

    private void validatePublishRequest(GroupTaskCreateRequest request) {
        if (request == null) {
            throw new IllegalArgumentException("发布请求不能为空");
        }
        if (request.getPublisherId() == null) {
            throw new IllegalArgumentException("发布人不能为空");
        }
        if (request.getRequiredCompleteCount() == null || request.getRequiredCompleteCount() <= 0) {
            throw new IllegalArgumentException("成团人数必须大于0");
        }
        if (request.getClaimTimeoutSeconds() == null || request.getClaimTimeoutSeconds() <= 0) {
            throw new IllegalArgumentException("完成时限必须大于0");
        }
    }

    private void validateProfile(UserEligibilityProfile profile) {
        if (profile == null || profile.getUserId() == null) {
            throw new IllegalArgumentException("用户画像或用户ID不能为空");
        }
    }

    private TaskAggregate requireTask(Long taskId) {
        TaskAggregate task = taskStore.get(taskId);
        if (task == null) {
            throw new IllegalArgumentException("任务不存在, taskId=" + taskId);
        }
        return task;
    }

    private int cleanExpiredClaims(TaskAggregate task, Instant now) {
        int removed = 0;
        Set<Long> timeoutUsers = new HashSet<>();
        for (Map.Entry<Long, ClaimContext> entry : task.getClaimingUsers().entrySet()) {
            if (now.isAfter(entry.getValue().getDeadline())) {
                timeoutUsers.add(entry.getKey());
            }
        }
        for (Long userId : timeoutUsers) {
            task.getClaimingUsers().remove(userId);
            removed++;
            log.info("任务接单超时回收, taskId={}, userId={}", task.getTaskId(), userId);
        }
        return removed;
    }

    private boolean matchesEligibility(TaskAggregate task, UserEligibilityProfile profile) {
        if (!CollectionUtils.isEmpty(task.getAllowedUserIds()) && !task.getAllowedUserIds().contains(profile.getUserId())) {
            return false;
        }

        if (task.getMinVipLevel() != null) {
            if (profile.getVipLevel() == null || profile.getVipLevel() < task.getMinVipLevel()) {
                return false;
            }
        }

        if (!CollectionUtils.isEmpty(task.getRequiredTags())) {
            if (CollectionUtils.isEmpty(profile.getTags())) {
                return false;
            }
            if (!profile.getTags().containsAll(task.getRequiredTags())) {
                return false;
            }
        }

        return true;
    }

    private <T> Set<T> toMutableSet(Set<T> source) {
        return source == null ? null : new HashSet<>(source);
    }

    @Data
    private static class TaskAggregate {
        private Long taskId;
        private Long publisherId;
        private int requiredCompleteCount;
        private long claimTimeoutSeconds;
        private Set<Long> allowedUserIds;
        private Integer minVipLevel;
        private Set<String> requiredTags;
        private GroupTaskStatus status;
        private Set<Long> completedUserIds = new HashSet<>();
        private Map<Long, ClaimContext> claimingUsers = new HashMap<>();
    }

    @Data
    private static class ClaimContext {
        private Instant claimTime;
        private Instant deadline;
    }
}
