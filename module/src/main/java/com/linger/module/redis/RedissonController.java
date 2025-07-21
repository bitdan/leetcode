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

    private final RedissonService redissonTaskService;

    @GetMapping("/grabTask")
    public String grab(@RequestParam String userId) {
        return redissonTaskService.grabTask(userId);
    }


    @PostMapping("/push")
    public ResponseEntity<String> pushDelayMessage(@RequestBody DelayMessageRequest request) {
        redissonTaskService.sendMsg(request);
        return ResponseEntity.ok("消息已延时发送");
    }
}
