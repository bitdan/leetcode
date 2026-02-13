package com.linger.module.groupbuy.model;

import lombok.AllArgsConstructor;
import lombok.Data;

/**
 * 拼团任务详情
 */
@Data
@AllArgsConstructor
public class GroupTaskDetail {

    private Long taskId;
    private Long publisherId;
    private int requiredCompleteCount;
    private int completedCount;
    private int claimingCount;
    private long claimTimeoutSeconds;
    private GroupTaskStatus status;
}
