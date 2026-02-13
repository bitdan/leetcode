package com.linger.module.redisson.model;

import lombok.Data;

/**
 * @description PurchaseRequest
 * @date 2026/2/12 11:03:24
 * @version 1.0
 */
@Data
public class PurchaseRequest {

    private Long userId;

    private String product;

    private Integer quantity;

    /**
     * 全局库存
     */
    private Integer globalLimit;

    /**
     * 过期时间（秒）
     */
    private Integer expireSeconds;
}
