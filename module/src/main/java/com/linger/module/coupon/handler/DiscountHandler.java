package com.linger.module.coupon.handler;

import com.linger.module.coupon.model.Coupon;
import com.linger.module.coupon.model.CouponContext;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.stream.Collectors;

/**
 * @version 1.0
 * @description DiscountHandler
 * @date 2025/7/24 16:56:27
 */
@Component
@Order(2)
public class DiscountHandler extends AbstractCouponHandler {
    @Override
    protected boolean canApply(CouponContext context) {
        return context.getOrder().getCoupons().stream()
                .filter(c -> "DISCOUNT".equals(c.getType()))
                .anyMatch(c -> !context.getAppliedCoupons().contains(c));
    }

    @Override
    protected void doApply(CouponContext context) {
        List<Coupon> discountCoupons = context.getOrder().getCoupons().stream()
                .filter(c -> "DISCOUNT".equals(c.getType()))
                .filter(c -> !context.getAppliedCoupons().contains(c))
                .collect(Collectors.toList());

        for (Coupon coupon : discountCoupons) {
            context.setCurrentPrice(context.getCurrentPrice() * coupon.getDiscountRate());
            context.getAppliedCoupons().add(coupon);
        }
    }
}
