package com.linger.module.groupbuy.transaction.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

@Data
public class CreateActivityRequest {
    private String name;
    private String skuId;
    private BigDecimal unitPrice;
    private Integer totalStock;
    private Integer perUserLimit;
    private Integer targetCount;
    private Long payTimeoutSeconds;
    private Long groupTimeoutSeconds;
    private OffsetDateTime startsAt;
    private OffsetDateTime endsAt;
}

