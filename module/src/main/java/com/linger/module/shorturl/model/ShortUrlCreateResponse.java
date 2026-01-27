package com.linger.module.shorturl.model;

import lombok.AllArgsConstructor;
import lombok.Data;

/**
 * 创建短链返回结果
 */
@Data
@AllArgsConstructor
public class ShortUrlCreateResponse {

    /**
     * 短链编码，例如 aB3k9
     */
    private String code;

    /**
     * 完整短链地址，例如 https://xxx.com/s/aB3k9
     */
    private String shortUrl;

    /**
     * 长链接
     */
    private String longUrl;

    /**
     * 过期时间戳（毫秒），为 null 表示不过期
     */
    private Long expireAt;
}


