package com.linger.module.redisson.controller;

import com.linger.module.redisson.model.DelayMessageRequest;
import com.linger.module.redisson.model.PurchaseRequest;
import com.linger.module.redisson.service.RedissonService;
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

    /**
     * 压测购买接口
     */
    @PostMapping("/purchase")
    public ResponseEntity<String> purchase(@RequestBody PurchaseRequest request) {

        redissonService.purchaseItem(
                request.getUserId(),
                request.getProduct(),
                request.getQuantity(),
                request.getGlobalLimit(),
                request.getExpireSeconds()
        );

        return ResponseEntity.ok("success");
    }

}
