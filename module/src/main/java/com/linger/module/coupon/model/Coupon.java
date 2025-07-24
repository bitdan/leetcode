package com.linger.module.coupon.model;

import lombok.Data;

/**
 * @version 1.0
 * @description Coupon
 * @date 2025/7/24 16:53:12
 */
@Data
public class Coupon {
    private Long id;
    private CouponType type; // FULL_REDUCTION/DISCOUNT/NO_THRESHOLD
    private Double threshold; // 满减门槛
    private Double discountAmount; // 优惠金额
    private Double discountRate; // 折扣率

    // 按类型定制的构造函数
    public static Coupon createFullReduction(Double threshold, Double discountAmount) {
        Coupon coupon = new Coupon();
        coupon.setType(CouponType.FULL_REDUCTION);
        coupon.setThreshold(threshold);
        coupon.setDiscountAmount(discountAmount);
        return coupon;
    }

    public static Coupon createDiscount(Double discountRate) {
        Coupon coupon = new Coupon();
        coupon.setType(CouponType.DISCOUNT);
        coupon.setDiscountRate(discountRate);
        return coupon;
    }

    public static Coupon createNoThreshold(Double discountAmount) {
        Coupon coupon = new Coupon();
        coupon.setType(CouponType.NO_THRESHOLD);
        coupon.setDiscountAmount(discountAmount);
        return coupon;
    }
}
