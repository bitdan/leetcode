package com.linger.module.jackson;

import com.linger.module.util.JsonUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.jackson.Jackson2ObjectMapperBuilderCustomizer;
import org.springframework.boot.autoconfigure.jackson.JacksonAutoConfiguration;
import org.springframework.context.annotation.Bean;

/**
 * @version 1.0
 * @description JsonAutoConfiguration
 * @date 2025/7/31 09:14:02
 */
@Slf4j
@AutoConfiguration(before = JacksonAutoConfiguration.class)
public class JsonAutoConfiguration {

    /**
     * springboot 在构建ObjectMapper时默认使用这个构建器
     *
     * @return
     */
    @Bean
    public Jackson2ObjectMapperBuilderCustomizer customizer() {
        return JsonUtils.CUSTOMIZER;
    }

}

