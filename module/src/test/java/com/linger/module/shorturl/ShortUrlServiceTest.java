package com.linger.module.shorturl;

import com.linger.module.shorturl.model.ShortUrlCreateRequest;
import com.linger.module.shorturl.model.ShortUrlCreateResponse;
import com.linger.module.shorturl.model.ShortUrlStats;
import com.linger.module.shorturl.service.ShortUrlService;
import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.junit.jupiter.SpringJUnitConfig;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 短链服务测试
 */
@Slf4j
@SpringBootTest
@SpringJUnitConfig
public class ShortUrlServiceTest {

    @Autowired
    private ShortUrlService shortUrlService;

    @Test
    public void testCreateAndResolveShortUrl() {
        ShortUrlCreateRequest request = new ShortUrlCreateRequest();
        request.setLongUrl("https://example.com/path?x=1");
        request.setExpireSeconds(3600L);
        request.setReuse(true);

        ShortUrlCreateResponse response = shortUrlService.createShortUrl(request, "127.0.0.1");
        assertNotNull(response);
        assertNotNull(response.getCode());
        assertFalse(response.getCode().isEmpty());
        log.info("created short url: {}", response);

        String longUrl = shortUrlService.resolveLongUrl(response.getCode());
        assertEquals(request.getLongUrl(), longUrl);

        ShortUrlStats stats = shortUrlService.getStats(response.getCode());
        assertNotNull(stats);
        assertEquals(response.getCode(), stats.getCode());
        assertEquals(1L, stats.getTotalVisits());
        assertNotNull(stats.getLastAccessTime());
    }

    @Test
    public void testReuseSameLongUrl() {
        ShortUrlCreateRequest request1 = new ShortUrlCreateRequest();
        request1.setLongUrl("https://example.com/reuse");
        request1.setReuse(true);

        ShortUrlCreateRequest request2 = new ShortUrlCreateRequest();
        request2.setLongUrl("https://example.com/reuse");
        request2.setReuse(true);

        ShortUrlCreateResponse r1 = shortUrlService.createShortUrl(request1, "127.0.0.1");
        ShortUrlCreateResponse r2 = shortUrlService.createShortUrl(request2, "127.0.0.1");

        assertNotNull(r1);
        assertNotNull(r2);
        assertEquals(r1.getCode(), r2.getCode(), "开启复用时，同一个长链应生成相同短链");
    }

    @Test
    public void testNoReuseGeneratesDifferentCodes() {
        ShortUrlCreateRequest request1 = new ShortUrlCreateRequest();
        request1.setLongUrl("https://example.com/no-reuse/1");
        request1.setReuse(false);

        ShortUrlCreateRequest request2 = new ShortUrlCreateRequest();
        request2.setLongUrl("https://example.com/no-reuse/2");
        request2.setReuse(false);

        ShortUrlCreateResponse r1 = shortUrlService.createShortUrl(request1, "127.0.0.1");
        ShortUrlCreateResponse r2 = shortUrlService.createShortUrl(request2, "127.0.0.1");

        assertNotNull(r1);
        assertNotNull(r2);
        assertNotEquals(r1.getCode(), r2.getCode(), "关闭复用时，不同长链应生成不同短链");
    }
}


