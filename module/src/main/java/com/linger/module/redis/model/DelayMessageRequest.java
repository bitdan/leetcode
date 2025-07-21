package com.linger.module.redis.model;

import lombok.Data;

/**
 * @version 1.0
 * @description DelayMessageRequest
 * @date 2025/7/21 18:55:24
 */
@Data
public class DelayMessageRequest {
    private Long id;
    private Long delaySecond;     // 延时时长
}
