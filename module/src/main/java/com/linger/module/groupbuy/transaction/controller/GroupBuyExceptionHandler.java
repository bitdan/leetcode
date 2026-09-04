package com.linger.module.groupbuy.transaction.controller;

import com.linger.module.groupbuy.transaction.dto.GroupBuyApiResponse;
import com.linger.module.groupbuy.transaction.exception.GroupBuyBusinessException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@Slf4j
@RestControllerAdvice(assignableTypes = GroupBuyTransactionController.class)
@ConditionalOnProperty(prefix = "groupbuy.transaction", name = "enabled", havingValue = "true")
public class GroupBuyExceptionHandler {

    @ExceptionHandler(GroupBuyBusinessException.class)
    public ResponseEntity<GroupBuyApiResponse<Void>> handleBusiness(GroupBuyBusinessException exception) {
        return ResponseEntity.status(HttpStatus.CONFLICT)
                .body(GroupBuyApiResponse.error(exception.getCode(), exception.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<GroupBuyApiResponse<Void>> handleUnexpected(Exception exception) {
        log.error("拼团交易接口异常", exception);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(GroupBuyApiResponse.error("INTERNAL_ERROR", "系统繁忙，请稍后重试"));
    }
}

