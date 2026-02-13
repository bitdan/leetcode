package com.linger.module.groupbuy.model;

import lombok.Builder;
import lombok.Data;

import java.util.Set;

/**
 * 接任务用户画像（用于资格校验）
 */
@Data
@Builder
public class UserEligibilityProfile {

    private Long userId;
    private Integer vipLevel;
    private Set<String> tags;
}
