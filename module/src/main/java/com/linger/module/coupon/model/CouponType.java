package com.linger.module.coupon.model;

public enum CouponType {
    FULL_REDUCTION(1),
    DISCOUNT(2),
    NO_THRESHOLD(3);

    private final int order;

    CouponType(int order) {
        this.order = order;
    }

    public int getOrder() {
        return order;
    }
} 
