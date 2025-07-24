package com.linger.module.coupon.model;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/**
 * @version 1.0
 * @description CouponContext
 * @date 2025/7/24 16:54:19
 */
@Data
public class CouponContext {
    private Order order;
    private Double currentPrice; // 链式处理中的当前价格
    private List<Coupon> appliedCoupons = new ArrayList<>();
}
