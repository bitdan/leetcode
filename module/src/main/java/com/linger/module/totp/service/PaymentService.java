package com.linger.module.totp.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RMap;
import org.redisson.api.RedissonClient;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Service
@RequiredArgsConstructor
@Slf4j
public class PaymentService {
    private final TotpService totpService;
    private final RedissonClient redissonClient;
    private static final String PAYMENT_RECORD_KEY = "payment:records";

    /**
     * 用TOTP备用码完成支付
     */
    public boolean payWithBackupCode(String userId, String code, BigDecimal amount) {
        // 校验备用码
        boolean valid = totpService.verifyBackupCode(userId, code);
        if (!valid) {
            log.warn("支付失败，备用码无效或已被使用: userId={}, code={}", userId, code);
            return false;
        }
        // 记录支付流水
        RMap<String, String> paymentMap = redissonClient.getMap(PAYMENT_RECORD_KEY);
        String record = String.format("userId=%s, amount=%s, code=%s, time=%s", userId, amount, code, LocalDateTime.now());
        paymentMap.put(userId + ":" + code, record);
        log.info("支付成功: {}", record);
        return true;
    }
} 