package com.linger.module.coupon.model;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/**
 * @version 1.0
 * @description Order
 * @date 2025/7/24 16:53:46
 */
@Data
public class Order {
    private Double originalPrice;
    private List<Coupon> coupons = new ArrayList<>();
    private Double finalPrice;

    public Order(Double originalPrice) {
        this.originalPrice = originalPrice;
    }
}
