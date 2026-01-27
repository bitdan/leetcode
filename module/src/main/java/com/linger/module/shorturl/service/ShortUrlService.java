package com.linger.module.shorturl.service;

import com.linger.module.shorturl.model.ShortUrlCreateRequest;
import com.linger.module.shorturl.model.ShortUrlCreateResponse;
import com.linger.module.shorturl.model.ShortUrlStats;

/**
 * 短链服务接口
 */
public interface ShortUrlService {

    /**
     * 创建短链
     */
    ShortUrlCreateResponse createShortUrl(ShortUrlCreateRequest request, String clientIp);

    /**
     * 根据短链 code 查询长链接
     */
    String resolveLongUrl(String code);

    /**
     * 获取短链统计信息
     */
    ShortUrlStats getStats(String code);
}


