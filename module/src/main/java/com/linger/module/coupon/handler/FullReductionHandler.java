package com.linger.module.coupon.handler;

import com.linger.module.coupon.model.CouponContext;
import com.linger.module.coupon.model.CouponType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * @version 1.0
 * @description FullReductionHandler
 * @date 2025/7/24 16:56:00
 */
@Component
@Order(1)
@Slf4j
public class FullReductionHandler extends AbstractCouponHandler {
    @Override
    protected boolean canApply(CouponContext context) {
        return context.getOrder().getCoupons().stream()
                .filter(c -> c.getType() == CouponType.FULL_REDUCTION)
                .anyMatch(c -> context.getCurrentPrice() >= c.getThreshold() &&
                        !context.getAppliedCoupons().contains(c));
    }

    @Override
    protected void doApply(CouponContext context) {
        double before = context.getCurrentPrice();

        context.getOrder().getCoupons().stream()
                .filter(c -> c.getType() == CouponType.FULL_REDUCTION)
                .filter(c -> context.getCurrentPrice() >= c.getThreshold())
                .filter(c -> !context.getAppliedCoupons().contains(c))
                .forEach(c -> {
                    double oldPrice = context.getCurrentPrice();
                    double newPrice = Math.max(0.01, oldPrice - c.getDiscountAmount());
                    context.setCurrentPrice(newPrice);
                    context.getAppliedCoupons().add(c);

                    log.info("应用满减券: {}元 -> {}元 (条件: 满{}减{})",
                            oldPrice, newPrice, c.getThreshold(), c.getDiscountAmount());
                });

        double after = context.getCurrentPrice();
        log.debug("满减券处理完成: {}元 -> {}元 (变化: -{}元)",
                before, after, before - after);
    }
}
