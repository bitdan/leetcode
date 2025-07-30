package com.linger.module.totp.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * @version 1.0
 * @description TOTP用户模型
 * @date 2025/7/30 15:47:04
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TotpUser {

    /**
     * 用户ID
     */
    private String userId;

    /**
     * TOTP密钥（Base32编码）
     */
    private String secretKey;

    /**
     * 是否启用TOTP
     */
    private Boolean enabled;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 最后使用时间
     */
    private LocalDateTime lastUsedTime;

    /**
     * 备用码（用于紧急情况）
     */
    private String backupCodes;
} 
