package com.linger.module.coupon.handler;

import com.linger.module.coupon.model.CouponContext;

/**
 * @version 1.0
 * @description AbstractCouponHandler
 * @date 2025/7/24 16:55:33
 */
public abstract class AbstractCouponHandler implements CouponHandler {
    private CouponHandler next;

    @Override
    public void setNext(CouponHandler next) {
        this.next = next;
    }

    @Override
    public void apply(CouponContext context) {
        if (canApply(context)) {
            doApply(context);
        }
        if (next != null) {
            next.apply(context);
        }
    }

    protected abstract boolean canApply(CouponContext context);

    protected abstract void doApply(CouponContext context);
}
