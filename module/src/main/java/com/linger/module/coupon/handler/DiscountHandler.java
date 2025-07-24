package com.linger.module.coupon.handler;

import com.linger.module.coupon.model.Coupon;
import com.linger.module.coupon.model.CouponContext;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.text.DecimalFormat;
import java.util.List;
import java.util.stream.Collectors;

/**
 * @version 1.0
 * @description DiscountHandler
 * @date 2025/7/24 16:56:27
 */
@Component
@Order(2)
@Slf4j
public class DiscountHandler extends AbstractCouponHandler {
    private static final DecimalFormat discountFormat = new DecimalFormat("#.#");

    @Override
    protected boolean canApply(CouponContext context) {
        return context.getOrder().getCoupons().stream()
                .filter(c -> "DISCOUNT".equals(c.getType()))
                .anyMatch(c -> !context.getAppliedCoupons().contains(c));
    }

    @Override
    protected void doApply(CouponContext context) {
        double before = context.getCurrentPrice();
        List<Coupon> coupons = context.getOrder().getCoupons().stream()
                .filter(c -> "DISCOUNT".equals(c.getType()))
                .filter(c -> !context.getAppliedCoupons().contains(c))
                .collect(Collectors.toList());

        for (Coupon coupon : coupons) {
            double discountRate = coupon.getDiscountRate();
            if (discountRate <= 0 || discountRate > 1) {
                log.warn("折扣券无效: 折扣率{}应在0-1范围内, 跳过处理", discountRate);
                continue;
            }

            double oldPrice = context.getCurrentPrice();
            double newPrice = oldPrice * discountRate;
            context.setCurrentPrice(newPrice);
            context.getAppliedCoupons().add(coupon);

            // 正确计算和显示折扣比例
            int discountPercent = (int) ((1 - discountRate) * 100);
            String discountDisplay = formatDiscount(discountRate);

            log.info("应用折扣券: {}元 -> {}元 ({}折, 优惠{}%)",
                    oldPrice, newPrice, discountDisplay, discountPercent);
        }

        double after = context.getCurrentPrice();
        if (!coupons.isEmpty()) {
            log.debug("折扣券处理完成: {}元 -> {}元 (变化: -{:.2f}元)",
                    before, after, before - after);
        }
    }

    // 格式化折扣显示
    private String formatDiscount(double discountRate) {
        // 计算实际折扣比例 (1/折扣率)
        double actualDiscount = 10 * discountRate;

        // 避免显示"10.0折"这样的情况
        if (actualDiscount >= 9.95) {
            return "无折扣";
        }

        return discountFormat.format(actualDiscount);
    }
}
