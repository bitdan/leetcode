package com.linger.module.redisson;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.redisson.codec.JsonJacksonCodec;
import org.redisson.spring.starter.RedissonAutoConfigurationCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.annotation.Resource;

/**
 * @version 1.0
 * @description RedissonConfig
 * @date 2025/7/30 16:51:42
 */
@Configuration
public class RedissonConfig {

    @Resource
    private ObjectMapper objectMapper;

    @Bean
    public RedissonAutoConfigurationCustomizer redissonCustomizer() {

        return config -> {
            JsonJacksonCodec codec = new JsonJacksonCodec(objectMapper);
            config.setCodec(codec);
        };
    }
}
