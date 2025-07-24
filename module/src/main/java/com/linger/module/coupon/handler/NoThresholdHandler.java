package com.linger.module.coupon.handler;

import com.linger.module.coupon.model.CouponContext;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * @version 1.0
 * @description NoThresholdHandler
 * @date 2025/7/24 16:56:58
 */
@Component
@Order(3)
public class NoThresholdHandler extends AbstractCouponHandler {
    @Override
    protected boolean canApply(CouponContext context) {
        return context.getOrder().getCoupons().stream()
                .filter(c -> "NO_THRESHOLD".equals(c.getType()))
                .anyMatch(c -> !context.getAppliedCoupons().contains(c));
    }

    @Override
    protected void doApply(CouponContext context) {
        context.getOrder().getCoupons().stream()
                .filter(c -> "NO_THRESHOLD".equals(c.getType()))
                .filter(c -> !context.getAppliedCoupons().contains(c))
                .forEach(c -> {
                    context.setCurrentPrice(context.getCurrentPrice() - c.getDiscountAmount());
                    context.getAppliedCoupons().add(c);
                });
    }
}
