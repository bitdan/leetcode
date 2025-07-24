package com.linger.module.coupon.handler;

import com.linger.module.coupon.model.CouponContext;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * @version 1.0
 * @description FullReductionHandler
 * @date 2025/7/24 16:56:00
 */
@Component
@Order(1)
public class FullReductionHandler extends AbstractCouponHandler {
    @Override
    protected boolean canApply(CouponContext context) {
        return context.getOrder().getCoupons().stream()
                .filter(c -> "FULL_REDUCTION".equals(c.getType()))
                .anyMatch(c -> context.getCurrentPrice() >= c.getThreshold() &&
                        !context.getAppliedCoupons().contains(c));
    }

    @Override
    protected void doApply(CouponContext context) {
        context.getOrder().getCoupons().stream()
                .filter(c -> "FULL_REDUCTION".equals(c.getType()))
                .filter(c -> context.getCurrentPrice() >= c.getThreshold())
                .filter(c -> !context.getAppliedCoupons().contains(c))
                .forEach(c -> {
                    context.setCurrentPrice(context.getCurrentPrice() - c.getDiscountAmount());
                    context.getAppliedCoupons().add(c);
                });
    }
}
