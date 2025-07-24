package com.linger.module.coupon.service;

import com.linger.module.coupon.handler.CouponHandler;
import com.linger.module.coupon.model.CouponContext;
import com.linger.module.coupon.model.Order;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.annotation.AnnotationAwareOrderComparator;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * @version 1.0
 * @description CouponChainService
 * @date 2025/7/24 16:57:24
 */
@Service
public class CouponChainService {
    private final CouponHandler firstHandler;

    @Autowired
    public CouponChainService(List<CouponHandler> handlers) {
        // 按@Order顺序排序并构建链
        handlers.sort(AnnotationAwareOrderComparator.INSTANCE);

        for (int i = 0; i < handlers.size() - 1; i++) {
            handlers.get(i).setNext(handlers.get(i + 1));
        }

        this.firstHandler = handlers.get(0);
    }

    public Order process(Order order) {
        CouponContext context = new CouponContext();
        context.setOrder(order);
        context.setCurrentPrice(order.getOriginalPrice());

        firstHandler.apply(context);

        order.setFinalPrice(context.getCurrentPrice());
        return order;
    }
}
