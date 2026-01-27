package com.linger.module.shorturl.model;

import lombok.Data;

/**
 * 创建短链入参
 */
@Data
public class ShortUrlCreateRequest {

    /**
     * 原始长链接，必须是完整的 URL
     */
    private String longUrl;

    /**
     * 过期时间，单位秒；为 null 或 <=0 表示不过期
     */
    private Long expireSeconds;

    /**
     * 同一个长链是否复用已有短链，默认 true
     */
    private Boolean reuse;
}


