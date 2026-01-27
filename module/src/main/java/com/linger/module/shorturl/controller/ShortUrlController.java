package com.linger.module.shorturl.controller;

import com.linger.module.shorturl.model.ShortUrlCreateRequest;
import com.linger.module.shorturl.model.ShortUrlCreateResponse;
import com.linger.module.shorturl.model.ShortUrlStats;
import com.linger.module.shorturl.service.ShortUrlService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.net.URI;

/**
 * 短链 REST 接口
 */
@RestController
@RequestMapping("/short-url")
@RequiredArgsConstructor
@Slf4j
public class ShortUrlController {

    private final ShortUrlService shortUrlService;

    /**
     * 创建短链
     */
    @PostMapping("/api")
    public ShortUrlCreateResponse create(@RequestBody ShortUrlCreateRequest request,
                                         HttpServletRequest httpRequest) {
        String clientIp = extractClientIp(httpRequest);
        ShortUrlCreateResponse response = shortUrlService.createShortUrl(request, clientIp);
        // 根据当前请求动态拼短链域名，避免修改配置
        if (response != null) {
            String base = buildBaseUrl(httpRequest);
            String shortUrl = base + "/short-url/r/" + response.getCode();
            response.setShortUrl(shortUrl);
        }
        return response;
    }

    /**
     * 短链跳转
     */
    @GetMapping("/r/{code}")
    public ResponseEntity<Void> redirect(@PathVariable("code") String code) {
        String longUrl = shortUrlService.resolveLongUrl(code);
        if (longUrl == null) {
            return ResponseEntity.notFound().build();
        }
        HttpHeaders headers = new HttpHeaders();
        headers.setLocation(URI.create(longUrl));
        return new ResponseEntity<>(headers, HttpStatus.FOUND);
    }

    /**
     * 查询短链统计
     */
    @GetMapping("/stats/{code}")
    public ResponseEntity<ShortUrlStats> stats(@PathVariable("code") String code) {
        ShortUrlStats stats = shortUrlService.getStats(code);
        if (stats == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(stats);
    }

    private String extractClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        return ip;
    }

    private String buildBaseUrl(HttpServletRequest request) {
        String scheme = request.getScheme();
        String host = request.getServerName();
        int port = request.getServerPort();
        if ((scheme.equals("http") && port == 80) || (scheme.equals("https") && port == 443)) {
            return scheme + "://" + host;
        }
        return scheme + "://" + host + ":" + port;
    }
}


