package com.linger.module.totp.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * @version 1.0
 * @description TOTP响应模型
 * @date 2025/7/30 15:47:04
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TotpResponse {

    /**
     * 是否成功
     */
    private Boolean success;

    /**
     * 消息
     */
    private String message;

    /**
     * 数据
     */
    private Object data;

    /**
     * 成功响应
     */
    public static TotpResponse success(String message) {
        return TotpResponse.builder()
                .success(true)
                .message(message)
                .build();
    }

    /**
     * 成功响应（带数据）
     */
    public static TotpResponse success(String message, Object data) {
        return TotpResponse.builder()
                .success(true)
                .message(message)
                .data(data)
                .build();
    }

    /**
     * 失败响应
     */
    public static TotpResponse error(String message) {
        return TotpResponse.builder()
                .success(false)
                .message(message)
                .build();
    }
} 
