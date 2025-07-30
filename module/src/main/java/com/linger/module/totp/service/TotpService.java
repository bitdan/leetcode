package com.linger.module.totp.service;

import com.linger.module.totp.TotpNative;
import com.linger.module.totp.model.TotpUser;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RMap;
import org.redisson.api.RedissonClient;
import org.springframework.stereotype.Service;

import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * @version 1.0
 * @description TOTP服务类
 * @date 2025/7/30 15:47:04
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class TotpService {

    private final RedissonClient redissonClient;

    private static final String TOTP_USER_KEY = "totp:users";
    private static final String TOTP_ATTEMPT_KEY = "totp:attempts";
    private static final String TOTP_BACKUP_CODES_KEY = "totp:backup_codes";

    // 验证码有效期（秒）
    private static final int TOTP_VALIDITY_PERIOD = 30;
    // 最大尝试次数
    private static final int MAX_ATTEMPTS = 5;
    // 尝试次数重置时间（分钟）
    private static final int ATTEMPT_RESET_MINUTES = 15;
    // 备用码数量
    private static final int BACKUP_CODES_COUNT = 10;

    /**
     * 为用户生成TOTP密钥
     */
    public TotpUser generateTotpForUser(String userId) {
        try {
            // 检查用户是否已存在
            RMap<String, TotpUser> userMap = redissonClient.getMap(TOTP_USER_KEY);
            if (userMap.containsKey(userId)) {
                throw new RuntimeException("用户已存在TOTP配置");
            }

            // 生成新的TOTP密钥
            String secretKey = TotpNative.generateSecret();

            // 生成备用码
            List<String> backupCodes = generateBackupCodes();

            // 创建TOTP用户
            TotpUser totpUser = TotpUser.builder()
                    .userId(userId)
                    .secretKey(secretKey)
                    .enabled(false) // 初始状态为未启用
                    .createTime(LocalDateTime.now())
                    .backupCodes(String.join(",", backupCodes))
                    .build();

            // 存储到Redis
            userMap.put(userId, totpUser);

            // 存储备用码（用于验证）
            RMap<String, String> backupCodesMap = redissonClient.getMap(TOTP_BACKUP_CODES_KEY);
            for (String code : backupCodes) {
                backupCodesMap.put(code, userId);
            }

            log.info("为用户 {} 生成TOTP密钥成功", userId);
            return totpUser;

        } catch (Exception e) {
            log.error("为用户 {} 生成TOTP密钥失败", userId, e);
            throw new RuntimeException("生成TOTP密钥失败: " + e.getMessage());
        }
    }

    /**
     * 验证TOTP码
     */
    public boolean verifyTotp(String userId, String totpCode) {
        try {
            // 检查尝试次数，是否被锁定
            if (isUserLocked(userId)) {
                throw new RuntimeException("账户已被锁定，请稍后再试");
            }

            // 获取用户TOTP配置
            RMap<String, TotpUser> userMap = redissonClient.getMap(TOTP_USER_KEY);
            TotpUser totpUser = userMap.get(userId);

            if (totpUser == null) {
                throw new RuntimeException("用户TOTP配置不存在");
            }

            // 验证备用码
            if (verifyBackupCode(userId, totpCode)) {
                log.info("用户 {} 使用备用码验证成功", userId);
                updateLastUsedTime(userId);
                resetAttempts(userId);
                return true;
            }

            // 允许±1时间步窗口验证（时间步长为30秒）
            long currentTimeStep = Instant.now().getEpochSecond() / 30;
            for (int i = -1; i <= 1; i++) {
                String expectedCode = TotpNative.generateTotpAtTime(totpUser.getSecretKey(), currentTimeStep + i);
                if (totpCode.equals(expectedCode)) {
                    log.info("用户 {} TOTP验证成功", userId);
                    updateLastUsedTime(userId);
                    resetAttempts(userId);
                    return true;
                }
            }

            // 验证失败，增加尝试次数
            incrementAttempts(userId);
            log.warn("用户 {} TOTP验证失败，尝试次数: {}", userId, getAttempts(userId));
            return false;

        } catch (NoSuchAlgorithmException | InvalidKeyException e) {
            log.error("TOTP验证异常", e);
            throw new RuntimeException("TOTP验证异常: " + e.getMessage());
        } catch (Exception e) {
            log.error("用户 {} TOTP验证失败", userId, e);
            throw new RuntimeException("TOTP验证失败: " + e.getMessage());
        }
    }

    /**
     * 启用TOTP
     */
    public boolean enableTotp(String userId, String totpCode) {
        try {
            // 先验证TOTP码
            if (!verifyTotp(userId, totpCode)) {
                return false;
            }

            // 启用TOTP
            RMap<String, TotpUser> userMap = redissonClient.getMap(TOTP_USER_KEY);
            TotpUser totpUser = userMap.get(userId);
            if (totpUser != null) {
                totpUser.setEnabled(true);
                userMap.put(userId, totpUser);
                log.info("用户 {} TOTP已启用", userId);
                return true;
            }

            return false;

        } catch (Exception e) {
            log.error("启用用户 {} TOTP失败", userId, e);
            return false;
        }
    }

    /**
     * 禁用TOTP
     */
    public boolean disableTotp(String userId) {
        try {
            RMap<String, TotpUser> userMap = redissonClient.getMap(TOTP_USER_KEY);
            TotpUser totpUser = userMap.get(userId);
            if (totpUser != null) {
                totpUser.setEnabled(false);
                userMap.put(userId, totpUser);
                log.info("用户 {} TOTP已禁用", userId);
                return true;
            }

            return false;

        } catch (Exception e) {
            log.error("禁用用户 {} TOTP失败", userId, e);
            return false;
        }
    }

    /**
     * 获取用户TOTP信息
     */
    public TotpUser getTotpUser(String userId) {
        RMap<String, TotpUser> userMap = redissonClient.getMap(TOTP_USER_KEY);
        return userMap.get(userId);
    }

    /**
     * 删除用户TOTP配置
     */
    public boolean deleteTotpUser(String userId) {
        try {
            RMap<String, TotpUser> userMap = redissonClient.getMap(TOTP_USER_KEY);
            TotpUser totpUser = userMap.get(userId);

            if (totpUser != null) {
                // 删除备用码
                if (totpUser.getBackupCodes() != null) {
                    RMap<String, String> backupCodesMap = redissonClient.getMap(TOTP_BACKUP_CODES_KEY);
                    Arrays.stream(totpUser.getBackupCodes().split(","))
                            .forEach(backupCodesMap::remove);
                }

                // 删除用户配置
                userMap.remove(userId);

                // 删除尝试次数记录
                RMap<String, Integer> attemptMap = redissonClient.getMap(TOTP_ATTEMPT_KEY);
                attemptMap.remove(userId);

                log.info("用户 {} TOTP配置已删除", userId);
                return true;
            }

            return false;

        } catch (Exception e) {
            log.error("删除用户 {} TOTP配置失败", userId, e);
            return false;
        }
    }

    /**
     * 生成备用码
     */
    private List<String> generateBackupCodes() {
        return Arrays.stream(new String[BACKUP_CODES_COUNT])
                .map(code -> String.format("%08d", (int) (Math.random() * 100000000)))
                .collect(java.util.stream.Collectors.toList());
    }

    /**
     * 验证备用码
     */
    private boolean verifyBackupCode(String userId, String code) {
        RMap<String, String> backupCodesMap = redissonClient.getMap(TOTP_BACKUP_CODES_KEY);
        String codeUserId = backupCodesMap.get(code);

        if (userId.equals(codeUserId)) {
            // 使用后删除备用码
            backupCodesMap.remove(code);
            return true;
        }

        return false;
    }

    /**
     * 检查用户是否被锁定
     */
    private boolean isUserLocked(String userId) {
        int attempts = getAttempts(userId);
        return attempts >= MAX_ATTEMPTS;
    }

    /**
     * 获取尝试次数
     */
    private int getAttempts(String userId) {
        RMap<String, Integer> attemptMap = redissonClient.getMap(TOTP_ATTEMPT_KEY);
        return attemptMap.getOrDefault(userId, 0);
    }

    /**
     * 增加尝试次数
     */
    private void incrementAttempts(String userId) {
        RMap<String, Integer> attemptMap = redissonClient.getMap(TOTP_ATTEMPT_KEY);
        int attempts = getAttempts(userId) + 1;
        attemptMap.put(userId, attempts);

        // 设置过期时间
        attemptMap.expire(ATTEMPT_RESET_MINUTES, TimeUnit.MINUTES);
    }

    /**
     * 重置尝试次数
     */
    private void resetAttempts(String userId) {
        RMap<String, Integer> attemptMap = redissonClient.getMap(TOTP_ATTEMPT_KEY);
        attemptMap.remove(userId);
    }

    /**
     * 更新最后使用时间
     */
    private void updateLastUsedTime(String userId) {
        RMap<String, TotpUser> userMap = redissonClient.getMap(TOTP_USER_KEY);
        TotpUser totpUser = userMap.get(userId);
        if (totpUser != null) {
            totpUser.setLastUsedTime(LocalDateTime.now());
            userMap.put(userId, totpUser);
        }
    }
} 
