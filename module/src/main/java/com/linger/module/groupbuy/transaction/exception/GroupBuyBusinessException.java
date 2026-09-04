package com.linger.module.groupbuy.transaction.exception;

import lombok.Getter;

@Getter
public class GroupBuyBusinessException extends RuntimeException {

    private final String code;

    public GroupBuyBusinessException(String code, String message) {
        super(message);
        this.code = code;
    }
}

