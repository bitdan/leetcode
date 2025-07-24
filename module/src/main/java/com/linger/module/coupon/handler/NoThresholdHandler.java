package com.linger.module.coupon.handler;

import com.linger.module.coupon.model.CouponContext;
import com.linger.module.coupon.model.CouponType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * @version 1.0
 * @description NoThresholdHandler
 * @date 2025/7/24 16:56:58
 */
@Component
@Order(3)
@Slf4j
public class NoThresholdHandler extends AbstractCouponHandler {
    @Override
    protected boolean canApply(CouponContext context) {
        return context.getOrder().getCoupons().stream()
                .filter(c -> c.getType() == CouponType.NO_THRESHOLD)
                .anyMatch(c -> !context.getAppliedCoupons().contains(c));
    }

    @Override
    protected void doApply(CouponContext context) {
        double before = context.getCurrentPrice();

        context.getOrder().getCoupons().stream()
                .filter(c -> c.getType() == CouponType.NO_THRESHOLD)
                .filter(c -> !context.getAppliedCoupons().contains(c))
                .forEach(c -> {
                    double oldPrice = context.getCurrentPrice();
                    double discountAmount = Math.min(oldPrice, c.getDiscountAmount());
                    double newPrice = Math.max(0, oldPrice - discountAmount);
                    context.setCurrentPrice(newPrice);
                    context.getAppliedCoupons().add(c);

                    // 如果优惠金额被部分应用
                    if (discountAmount < c.getDiscountAmount()) {
                        log.info("应用无门槛券(部分): {}元 -> {}元 (优惠:{}, 实际使用:{})",
                                oldPrice, newPrice, c.getDiscountAmount(), discountAmount);
                    } else {
                        log.info("应用无门槛券: {}元 -> {}元 (优惠:{}元)",
                                oldPrice, newPrice, c.getDiscountAmount());
                    }
                });

        double after = context.getCurrentPrice();
        log.debug("无门槛券处理完成: {}元 -> {}元 (变化: -{}元)",
                before, after, before - after);
    }
}
