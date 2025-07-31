package com.linger.module.redisson;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RList;
import org.redisson.api.RedissonClient;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

/**
 * @version 1.0
 * @description RedissonInitializer
 * @date 2025/7/21 17:38:07
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class RedissonInitializer implements CommandLineRunner {

    private final RedissonClient redissonClient;

    @Override
    public void run(String... args) {
        RList<String> taskList = redissonClient.getList("tasks:available");
        taskList.clear(); // 先清空旧任务

        List<String> taskIds = IntStream.rangeClosed(1, 10)
                .mapToObj(i -> "task" + i)
                .collect(Collectors.toList());

        taskList.addAll(taskIds);
        log.info("Redisson 初始化任务池完成");
    }
}

