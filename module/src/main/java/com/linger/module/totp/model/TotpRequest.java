package com.linger.module.totp.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * @version 1.0
 * @description TOTP请求模型
 * @date 2025/7/30 15:47:04
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TotpRequest {

    /**
     * 用户ID
     */
    private String userId;

    /**
     * TOTP验证码（6位数字）
     */
    private String totpCode;
} 
