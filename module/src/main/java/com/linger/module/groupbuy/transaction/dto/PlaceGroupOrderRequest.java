package com.linger.module.groupbuy.transaction.dto;

import lombok.Data;

@Data
public class PlaceGroupOrderRequest {
    private String requestId;
    private Long userId;
    private Long activityId;
    private Long groupId;
    private Integer quantity;
}

