package com.linger.module.groupbuy.transaction.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

@Data
public class PaymentCallbackRequest {
    private String orderId;
    private String paymentNo;
    private BigDecimal paidAmount;
    private OffsetDateTime paidAt;
}

