package com.linger.module.totp;

import com.linger.module.totp.model.TotpUser;
import com.linger.module.totp.service.PaymentService;
import com.linger.module.totp.service.TotpService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.math.BigDecimal;
import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

@SpringBootTest
public class PaymentServiceTest {
    @Autowired
    private PaymentService paymentService;
    @Autowired
    private TotpService totpService;
    private String userId = "testUser";

    @BeforeEach
    public void setup() {
        totpService.deleteTotpUser(userId);
        totpService.generateTotpForUser(userId);
    }

    @Test
    public void testPayWithValidBackupCode() {
        TotpUser user = totpService.getTotpUser(userId);
        List<String> codes = Arrays.asList(user.getBackupCodes().split(","));
        String code = codes.get(0);
        boolean result = paymentService.payWithBackupCode(userId, code, new BigDecimal("100.00"));
        assertTrue(result, "支付应成功");
        // 再次使用同一个码应失败
        boolean result2 = paymentService.payWithBackupCode(userId, code, new BigDecimal("100.00"));
        assertFalse(result2, "同一个码不能重复使用");
    }

    @Test
    public void testPayWithInvalidBackupCode() {
        boolean result = paymentService.payWithBackupCode(userId, "invalidcode", new BigDecimal("50.00"));
        assertFalse(result, "无效码支付应失败");
    }
} 
