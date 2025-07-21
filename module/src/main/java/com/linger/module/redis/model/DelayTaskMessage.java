package com.linger.module.redis.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * @version 1.0
 * @description DelayTaskMessage
 * @date 2025/7/21 19:08:54
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class DelayTaskMessage {
    private Long id;
    private String type;
}
