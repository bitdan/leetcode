package com.linger.module.redis;

import com.linger.module.redis.model.DelayMessageRequest;
import com.linger.module.redis.service.RedissonService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * @version 1.0
 * @description RedissonController
 * @date 2025/7/21 17:36:59
 */
@RestController
@RequiredArgsConstructor
@RequestMapping("/redis")
public class RedissonController {

    private final RedissonService redissonService;

    @GetMapping("/grabTask")
    public String grab(@RequestParam String userId) {
        return redissonService.grabTask(userId);
    }

    @PostMapping("/push")
    public ResponseEntity<String> pushDelayMessage(@RequestBody DelayMessageRequest request) {
        redissonService.sendMsg(request);
        return ResponseEntity.ok("消息已延时发送");
    }

    private static final int DEFAULT_EXPIRY = 24 * 60 * 60; // 24小时


    @PostMapping("/purchase")
    public ResponseEntity<String> purchaseItem(
            @RequestParam Long userId,
            @RequestParam String productId,
            @RequestParam(defaultValue = "1") int purchaseLimit) {

        boolean success = redissonService.purchaseItem(
                userId,
                productId,
                purchaseLimit,
                DEFAULT_EXPIRY
        );

        if (success) {
            return ResponseEntity.ok("购买成功");
        } else {
            return ResponseEntity.badRequest().body("购买失败：已达购买上限");
        }
    }
}
