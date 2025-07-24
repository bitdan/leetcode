package com.linger.module.coupon.handler;

import com.linger.module.coupon.model.CouponContext;

/**
 * @version 1.0
 * @description CouponHandler
 * @date 2025/7/24 16:55:09
 */
public interface CouponHandler {
    void setNext(CouponHandler next);

    void apply(CouponContext context);
}
