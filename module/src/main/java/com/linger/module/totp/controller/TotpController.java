package com.linger.module.totp.controller;

import com.linger.module.totp.model.TotpRequest;
import com.linger.module.totp.model.TotpResponse;
import com.linger.module.totp.model.TotpUser;
import com.linger.module.totp.service.TotpService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

/**
 * @version 1.0
 * @description TOTP控制器
 * @date 2025/7/30 15:47:04
 */
@RestController
@RequestMapping("/api/totp")
@RequiredArgsConstructor
@Slf4j
public class TotpController {

    private final TotpService totpService;

    /**
     * 为用户生成TOTP密钥
     */
    @PostMapping("/generate/{userId}")
    public TotpResponse generateTotp(@PathVariable String userId) {
        try {
            if (userId == null || userId.trim().isEmpty()) {
                return TotpResponse.error("用户ID不能为空");
            }

            TotpUser totpUser = totpService.generateTotpForUser(userId);

            // 返回密钥和备用码（实际使用时应该通过安全渠道传递）
            Map<String, Object> data = new HashMap<>();
            data.put("secretKey", totpUser.getSecretKey());
            data.put("backupCodes", totpUser.getBackupCodes().split(","));
            data.put("qrCodeUrl", generateQrCodeUrl(totpUser.getSecretKey(), userId));

            return TotpResponse.success("TOTP密钥生成成功", data);

        } catch (Exception e) {
            log.error("生成TOTP密钥失败", e);
            return TotpResponse.error("生成TOTP密钥失败: " + e.getMessage());
        }
    }

    /**
     * 验证TOTP码
     */
    @PostMapping("/verify")
    public TotpResponse verifyTotp(@RequestBody TotpRequest request) {
        try {
            if (request.getUserId() == null || request.getUserId().trim().isEmpty()) {
                return TotpResponse.error("用户ID不能为空");
            }

            if (request.getTotpCode() == null || request.getTotpCode().trim().isEmpty()) {
                return TotpResponse.error("验证码不能为空");
            }

            if (request.getTotpCode().length() != 6) {
                return TotpResponse.error("验证码必须是6位数字");
            }

            boolean isValid = totpService.verifyTotp(request.getUserId(), request.getTotpCode());

            if (isValid) {
                return TotpResponse.success("TOTP验证成功");
            } else {
                return TotpResponse.error("TOTP验证失败");
            }

        } catch (Exception e) {
            log.error("TOTP验证失败", e);
            return TotpResponse.error("TOTP验证失败: " + e.getMessage());
        }
    }

    /**
     * 启用TOTP
     */
    @PostMapping("/enable")
    public TotpResponse enableTotp(@RequestBody TotpRequest request) {
        try {
            if (request.getUserId() == null || request.getUserId().trim().isEmpty()) {
                return TotpResponse.error("用户ID不能为空");
            }

            if (request.getTotpCode() == null || request.getTotpCode().trim().isEmpty()) {
                return TotpResponse.error("验证码不能为空");
            }

            boolean success = totpService.enableTotp(request.getUserId(), request.getTotpCode());

            if (success) {
                return TotpResponse.success("TOTP启用成功");
            } else {
                return TotpResponse.error("TOTP启用失败，请检查验证码");
            }

        } catch (Exception e) {
            log.error("启用TOTP失败", e);
            return TotpResponse.error("启用TOTP失败: " + e.getMessage());
        }
    }

    /**
     * 禁用TOTP
     */
    @PostMapping("/disable/{userId}")
    public TotpResponse disableTotp(@PathVariable String userId) {
        try {
            if (userId == null || userId.trim().isEmpty()) {
                return TotpResponse.error("用户ID不能为空");
            }

            boolean success = totpService.disableTotp(userId);

            if (success) {
                return TotpResponse.success("TOTP禁用成功");
            } else {
                return TotpResponse.error("TOTP禁用失败");
            }

        } catch (Exception e) {
            log.error("禁用TOTP失败", e);
            return TotpResponse.error("禁用TOTP失败: " + e.getMessage());
        }
    }

    /**
     * 获取用户TOTP信息
     */
    @GetMapping("/info/{userId}")
    public TotpResponse getTotpInfo(@PathVariable String userId) {
        try {
            if (userId == null || userId.trim().isEmpty()) {
                return TotpResponse.error("用户ID不能为空");
            }

            TotpUser totpUser = totpService.getTotpUser(userId);

            if (totpUser != null) {
                // 不返回敏感信息
                Map<String, Object> data = new HashMap<>();
                data.put("userId", totpUser.getUserId());
                data.put("enabled", totpUser.getEnabled());
                data.put("createTime", totpUser.getCreateTime());
                data.put("lastUsedTime", totpUser.getLastUsedTime());

                return TotpResponse.success("获取TOTP信息成功", data);
            } else {
                return TotpResponse.error("用户TOTP配置不存在");
            }

        } catch (Exception e) {
            log.error("获取TOTP信息失败", e);
            return TotpResponse.error("获取TOTP信息失败: " + e.getMessage());
        }
    }

    /**
     * 删除用户TOTP配置
     */
    @DeleteMapping("/delete/{userId}")
    public TotpResponse deleteTotp(@PathVariable String userId) {
        try {
            if (userId == null || userId.trim().isEmpty()) {
                return TotpResponse.error("用户ID不能为空");
            }

            boolean success = totpService.deleteTotpUser(userId);

            if (success) {
                return TotpResponse.success("TOTP配置删除成功");
            } else {
                return TotpResponse.error("TOTP配置删除失败");
            }

        } catch (Exception e) {
            log.error("删除TOTP配置失败", e);
            return TotpResponse.error("删除TOTP配置失败: " + e.getMessage());
        }
    }

    /**
     * 生成二维码URL（用于Google Authenticator等应用）
     */
    private String generateQrCodeUrl(String secretKey, String userId) {
        String issuer = "MyApp";
        String accountName = userId;

        // 生成otpauth URL格式
        return String.format("otpauth://totp/%s:%s?secret=%s&issuer=%s",
                issuer, accountName, secretKey, issuer);
    }
} 
