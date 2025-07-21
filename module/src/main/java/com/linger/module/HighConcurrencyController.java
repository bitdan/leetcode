package com.linger.module;

import com.linger.module.service.RedissonTaskService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * @version 1.0
 * @description HighConcurrencyController
 * @date 2025/7/21 17:36:59
 */
@RestController
@RequiredArgsConstructor
public class HighConcurrencyController {

    private final RedissonTaskService redissonTaskService;

    @GetMapping("/api/grabTask")
    public String grab(@RequestParam String userId) {
        return redissonTaskService.grabTask(userId);
    }
}
