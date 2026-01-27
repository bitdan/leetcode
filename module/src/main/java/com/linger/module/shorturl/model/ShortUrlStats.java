package com.linger.module.shorturl.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 短链访问统计
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ShortUrlStats {

    /**
     * 短链编码
     */
    private String code;

    /**
     * 总访问次数
     */
    private long totalVisits;

    /**
     * 最近一次访问时间（毫秒时间戳）
     */
    private Long lastAccessTime;
}


