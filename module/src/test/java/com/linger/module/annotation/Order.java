package com.linger.module.annotation;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * @description Order
 * @date 2025/12/11 18:59:27
 * @version 1.0
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
class Order {
    private Long id;
    private String name;
}
