package com.linger.module.groupbuy.transaction.model;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class ReservationResult {

    public enum Code {
        SUCCESS,
        DUPLICATE,
        OUT_OF_STOCK,
        GROUP_FULL,
        ALREADY_JOINED,
        ACTIVITY_NOT_RUNNING,
        GROUP_NOT_OPEN,
        USER_LIMIT_REACHED,
        RESERVATION_NOT_FOUND
    }

    private Code code;
    private String orderId;

    public boolean isAccepted() {
        return code == Code.SUCCESS || code == Code.DUPLICATE;
    }
}

