package com.linger.module.totp;

import com.linger.module.totp.model.TotpUser;
import com.linger.module.totp.service.TotpService;
import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import static org.junit.jupiter.api.Assertions.*;

/**
 * @version 1.0
 * @description TOTP服务测试
 * @date 2025/7/30 15:47:04
 */
@SpringBootTest
@Slf4j
public class TotpServiceTest {

    @Autowired
    private TotpService totpService;


    @Test
    public void run() {
        log.info("=== TOTP 系统演示开始 ===");

        String userId = "demoUser";

        try {
            // 1. 生成 TOTP 密钥
            log.info("1. 为用户 {} 生成 TOTP 密钥", userId);
            TotpUser totpUser = totpService.generateTotpForUser(userId);
            log.info("   生成的密钥: {}", totpUser.getSecretKey());
            log.info("   备用码: {}", totpUser.getBackupCodes());

            // 2. 生成当前 TOTP 码
            log.info("2. 生成当前 TOTP 码");
            String currentTotp = TotpNative.generateTotp(totpUser.getSecretKey());
            log.info("   当前 TOTP 码: {}", currentTotp);

            // 3. 验证 TOTP 码（应该失败，因为还未启用）
//            log.info("3. 验证 TOTP 码（未启用状态）");
//            boolean result = totpService.verifyTotp(userId, currentTotp);
//            log.info("   验证结果: {}", result);

            // 4. 启用 TOTP
            log.info("4. 启用 TOTP");
            boolean enabled = totpService.enableTotp(userId, currentTotp);
            log.info("   启用结果: {}", enabled);

            // 5. 再次验证 TOTP 码（应该成功）
            log.info("5. 验证 TOTP 码（已启用状态）");
            boolean result = totpService.verifyTotp(userId, currentTotp);
            log.info("   验证结果: {}", result);

            // 6. 测试备用码
            log.info("6. 测试备用码");
            String[] backupCodes = totpUser.getBackupCodes().split(",");
            result = totpService.verifyTotp(userId, backupCodes[0]);
            log.info("   备用码验证结果: {}", result);

            // 7. 获取用户信息
            log.info("7. 获取用户信息");
            TotpUser userInfo = totpService.getTotpUser(userId);
            log.info("   用户信息: userId={}, enabled={}, createTime={}",
                    userInfo.getUserId(), userInfo.getEnabled(), userInfo.getCreateTime());

            // 8. 禁用 TOTP
            log.info("8. 禁用 TOTP");
            boolean disabled = totpService.disableTotp(userId);
            log.info("   禁用结果: {}", disabled);

            // 9. 删除 TOTP 配置
            log.info("9. 删除 TOTP 配置");
            boolean deleted = totpService.deleteTotpUser(userId);
            log.info("   删除结果: {}", deleted);

            log.info("=== TOTP 系统演示完成 ===");

        } catch (Exception e) {
            log.error("TOTP 演示过程中发生错误", e);
        }
    }

    @Test
    public void testGenerateTotp() {
        String userId = "testUser001";

        // 生成TOTP密钥
        TotpUser totpUser = totpService.generateTotpForUser(userId);

        assertNotNull(totpUser);
        assertEquals(userId, totpUser.getUserId());
        assertNotNull(totpUser.getSecretKey());
        assertFalse(totpUser.getEnabled());
        assertNotNull(totpUser.getBackupCodes());

        log.info("生成的TOTP用户: {}", totpUser);
    }

    @Test
    public void testVerifyTotp() throws Exception {
        String userId = "testUser002";

        // 生成TOTP密钥
        TotpUser totpUser = totpService.generateTotpForUser(userId);

        // 生成当前TOTP码
        String currentTotp = TotpNative.generateTotp(totpUser.getSecretKey());
        log.info("当前TOTP码: {}", currentTotp);

        // 验证TOTP码（应该失败，因为还未启用）
        boolean result = totpService.verifyTotp(userId, currentTotp);
        assertFalse(result);

        // 启用TOTP
        boolean enabled = totpService.enableTotp(userId, currentTotp);
        assertTrue(enabled);

        // 再次验证TOTP码（应该成功）
        result = totpService.verifyTotp(userId, currentTotp);
        assertTrue(result);
    }

    @Test
    public void testBackupCodes() throws Exception {
        String userId = "testUser003";

        // 生成TOTP密钥
        TotpUser totpUser = totpService.generateTotpForUser(userId);
        String[] backupCodes = totpUser.getBackupCodes().split(",");

        // 启用TOTP（使用TOTP码）
        String currentTotp = TotpNative.generateTotp(totpUser.getSecretKey());
        boolean enabled = totpService.enableTotp(userId, currentTotp);
        assertTrue(enabled);

        // 使用备用码验证
        boolean result = totpService.verifyTotp(userId, backupCodes[0]);
        assertTrue(result);

        // 备用码使用后应该失效
        result = totpService.verifyTotp(userId, backupCodes[0]);
        assertFalse(result);
    }

    @Test
    public void testMaxAttempts() throws Exception {
        String userId = "testUser004";

        // 生成并启用TOTP
        TotpUser totpUser = totpService.generateTotpForUser(userId);
        String currentTotp = TotpNative.generateTotp(totpUser.getSecretKey());
        totpService.enableTotp(userId, currentTotp);

        // 多次使用错误码
        for (int i = 0; i < 5; i++) {
            boolean result = totpService.verifyTotp(userId, "000000");
            assertFalse(result);
        }

        // 第6次应该被锁定
        try {
            totpService.verifyTotp(userId, "000000");
            fail("应该抛出锁定异常");
        } catch (RuntimeException e) {
            assertTrue(e.getMessage().contains("锁定"));
        }
    }

    @Test
    public void testTotpLifecycle() {
        String userId = "testUser005";

        // 1. 生成TOTP
        TotpUser totpUser = totpService.generateTotpForUser(userId);
        assertNotNull(totpUser);

        // 2. 获取信息
        TotpUser info = totpService.getTotpUser(userId);
        assertNotNull(info);
        assertEquals(userId, info.getUserId());

        // 3. 禁用TOTP
        boolean disabled = totpService.disableTotp(userId);
        assertTrue(disabled);

        // 4. 删除TOTP
        boolean deleted = totpService.deleteTotpUser(userId);
        assertTrue(deleted);

        // 5. 验证删除
        TotpUser deletedInfo = totpService.getTotpUser(userId);
        assertNull(deletedInfo);
    }
} 
