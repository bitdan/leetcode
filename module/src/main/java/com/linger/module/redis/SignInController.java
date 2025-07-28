package com.linger.module.redis;

import com.linger.module.redis.service.SignInService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

/**
 * 签到功能控制器
 */
@RestController
@RequestMapping("/api/signin")
@RequiredArgsConstructor
@Slf4j
public class SignInController {

    private final SignInService signInService;

    /**
     * 用户签到
     */
    @PostMapping("/sign")
    public Map<String, Object> signIn(@RequestParam Long userId,
                                      @RequestParam(required = false) String date) {
        Map<String, Object> result = new HashMap<>();

        try {
            // 如果没有指定日期，使用今天
            String signDate = date != null ? date : LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));

            String signResult = signInService.signIn(userId, signDate);
            int consecutiveDays = signInService.getConsecutiveSignInDays(userId, signDate);

            result.put("success", true);
            result.put("message", signResult);
            result.put("consecutiveDays", consecutiveDays);
            result.put("signDate", signDate);

        } catch (Exception e) {
            log.error("签到异常，userId: {}", userId, e);
            result.put("success", false);
            result.put("message", "签到失败：" + e.getMessage());
        }

        return result;
    }

    /**
     * 查询签到状态
     */
    @GetMapping("/status")
    public Map<String, Object> getSignInStatus(@RequestParam Long userId,
                                               @RequestParam(required = false) String date) {
        Map<String, Object> result = new HashMap<>();

        try {
            String queryDate = date != null ? date : LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));

            boolean isSigned = signInService.isSignedIn(userId, queryDate);
            int consecutiveDays = signInService.getConsecutiveSignInDays(userId, queryDate);

            result.put("success", true);
            result.put("isSigned", isSigned);
            result.put("consecutiveDays", consecutiveDays);
            result.put("queryDate", queryDate);

        } catch (Exception e) {
            log.error("查询签到状态异常，userId: {}", userId, e);
            result.put("success", false);
            result.put("message", "查询失败：" + e.getMessage());
        }

        return result;
    }

    /**
     * 获取月度签到统计
     */
    @GetMapping("/stats/monthly")
    public Map<String, Object> getMonthlyStats(@RequestParam Long userId,
                                               @RequestParam(required = false) String yearMonth) {
        Map<String, Object> result = new HashMap<>();

        try {
            String queryMonth = yearMonth != null ? yearMonth :
                    LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM"));

            String stats = signInService.getMonthlySignInStats(userId, queryMonth);

            result.put("success", true);
            result.put("stats", stats);
            result.put("yearMonth", queryMonth);

        } catch (Exception e) {
            log.error("查询月度统计异常，userId: {}", userId, e);
            result.put("success", false);
            result.put("message", "查询失败：" + e.getMessage());
        }

        return result;
    }

    /**
     * 获取年度签到统计
     */
    @GetMapping("/stats/yearly")
    public Map<String, Object> getYearlyStats(@RequestParam Long userId,
                                              @RequestParam(required = false) Integer year) {
        Map<String, Object> result = new HashMap<>();

        try {
            int queryYear = year != null ? year : LocalDate.now().getYear();

            String stats = signInService.getYearlySignInStats(userId, queryYear);

            result.put("success", true);
            result.put("stats", stats);
            result.put("year", queryYear);

        } catch (Exception e) {
            log.error("查询年度统计异常，userId: {}", userId, e);
            result.put("success", false);
            result.put("message", "查询失败：" + e.getMessage());
        }

        return result;
    }

    /**
     * 获取指定日期范围的签到记录
     */
    @GetMapping("/range")
    public Map<String, Object> getSignInRange(@RequestParam Long userId,
                                              @RequestParam String startDate,
                                              @RequestParam String endDate) {
        Map<String, Object> result = new HashMap<>();

        try {
            String rangeStats = signInService.getSignInStatusRange(userId, startDate, endDate);

            result.put("success", true);
            result.put("rangeStats", rangeStats);
            result.put("startDate", startDate);
            result.put("endDate", endDate);

        } catch (Exception e) {
            log.error("查询签到范围异常，userId: {}, startDate: {}, endDate: {}",
                    userId, startDate, endDate, e);
            result.put("success", false);
            result.put("message", "查询失败：" + e.getMessage());
        }

        return result;
    }

    /**
     * 获取连续签到天数
     */
    @GetMapping("/consecutive")
    public Map<String, Object> getConsecutiveDays(@RequestParam Long userId,
                                                  @RequestParam(required = false) String date) {
        Map<String, Object> result = new HashMap<>();

        try {
            String queryDate = date != null ? date : LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));

            int consecutiveDays = signInService.getConsecutiveSignInDays(userId, queryDate);

            result.put("success", true);
            result.put("consecutiveDays", consecutiveDays);
            result.put("queryDate", queryDate);

        } catch (Exception e) {
            log.error("查询连续签到天数异常，userId: {}", userId, e);
            result.put("success", false);
            result.put("message", "查询失败：" + e.getMessage());
        }

        return result;
    }
} 
