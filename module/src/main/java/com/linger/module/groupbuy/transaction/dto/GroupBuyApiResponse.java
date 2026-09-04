package com.linger.module.groupbuy.transaction.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class GroupBuyApiResponse<T> {
    private boolean success;
    private String code;
    private String message;
    private T data;

    public static <T> GroupBuyApiResponse<T> success(T data) {
        return new GroupBuyApiResponse<>(true, "SUCCESS", "success", data);
    }

    public static <T> GroupBuyApiResponse<T> error(String code, String message) {
        return new GroupBuyApiResponse<>(false, code, message, null);
    }
}

