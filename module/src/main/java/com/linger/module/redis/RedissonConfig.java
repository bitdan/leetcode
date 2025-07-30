package com.linger.module.redis;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.redisson.Redisson;
import org.redisson.api.RedissonClient;
import org.redisson.codec.JsonJacksonCodec;
import org.redisson.config.Config;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;

import javax.annotation.Resource;
import java.io.IOException;

/**
 * @version 1.0
 * @description RedissonConfig
 * @date 2025/7/30 16:51:42
 */
@Configuration
public class RedissonConfig {

    @Resource
    private ObjectMapper objectMapper;

    @Bean(destroyMethod = "shutdown")
    public RedissonClient redissonClient() throws IOException {
        // 读取配置文件
        Config config = Config.fromYAML(new ClassPathResource("redisson.yml").getInputStream());

        // 使用统一 ObjectMapper 创建 codec
        JsonJacksonCodec codec = new JsonJacksonCodec(objectMapper);
        config.setCodec(codec); // 覆盖 codec

        return Redisson.create(config);
    }
}
