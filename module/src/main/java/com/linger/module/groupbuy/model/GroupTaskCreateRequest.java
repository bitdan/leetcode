package com.linger.module.groupbuy.model;

import lombok.Data;

import java.util.Set;

/**
 * 拼团任务发布请求
 */
@Data
public class GroupTaskCreateRequest {

    /**
     * 发布人ID
     */
    private Long publisherId;

    /**
     * 成团需要的最终完成人数
     */
    private Integer requiredCompleteCount;

    /**
     * 接单后允许的完成时限（秒）
     */
    private Long claimTimeoutSeconds;

    /**
     * 限定可参与用户，空表示不限制
     */
    private Set<Long> allowedUserIds;

    /**
     * 参与者最小会员等级，空表示不限制
     */
    private Integer minVipLevel;

    /**
     * 参与者必须具备的标签，空表示不限制
     */
    private Set<String> requiredTags;
}
