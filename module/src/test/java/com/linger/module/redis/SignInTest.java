package com.linger.module.redis;

import com.linger.module.redis.service.SignInService;
import com.linger.module.util.DateUtil;
import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

import javax.annotation.Resource;

/**
 * 签到功能测试类
 */
@SpringBootTest

@Slf4j
public class SignInTest {

    @Resource
    private SignInService signInService;

    @Test
    public void testSignInFunctionality() {
        Long userId = 1001L;
        String today = DateUtil.getTodayString();
        String yesterday = DateUtil.getYesterdayString();
        String tomorrow = DateUtil.getTomorrowString();

        log.info("=== 签到功能测试开始 ===");

        // 1. 测试签到
        log.info("1. 测试用户签到");
        String result1 = signInService.signIn(userId, today);
        log.info("今日签到结果: {}", result1);

        // 重复签到测试
        String result2 = signInService.signIn(userId, today);
        log.info("重复签到结果: {}", result2);

        // 2. 测试查询签到状态
        log.info("\n2. 测试查询签到状态");
        boolean isTodaySigned = signInService.isSignedIn(userId, today);
        boolean isYesterdaySigned = signInService.isSignedIn(userId, yesterday);
        log.info("今日是否已签到: {}", isTodaySigned);
        log.info("昨日是否已签到: {}", isYesterdaySigned);

        // 3. 测试连续签到天数
        log.info("\n3. 测试连续签到天数");
        // 先给昨天签到
        signInService.signIn(userId, yesterday);
        int consecutiveDays = signInService.getConsecutiveSignInDays(userId, today);
        log.info("连续签到天数: {}", consecutiveDays);

        // 4. 测试月度签到统计
        log.info("\n4. 测试月度签到统计");
        String currentMonth = DateUtil.getCurrentYear() + "-" + String.format("%02d", DateUtil.getCurrentMonth());
        String monthlyStats = signInService.getMonthlySignInStats(userId, currentMonth);
        log.info("月度统计: {}", monthlyStats);

        // 5. 测试年度签到统计
        log.info("\n5. 测试年度签到统计");
        int currentYear = DateUtil.getCurrentYear();
        String yearlyStats = signInService.getYearlySignInStats(userId, currentYear);
        log.info("年度统计: {}", yearlyStats);

        // 6. 测试批量查询签到状态
        log.info("\n6. 测试批量查询签到状态");
        String startDate = DateUtil.getDaysBefore(today, 7);
        String endDate = today;
        String rangeStats = signInService.getSignInStatusRange(userId, startDate, endDate);
        log.info("最近7天签到记录:\n{}", rangeStats);

        log.info("\n=== 签到功能测试结束 ===");
    }

    @Test
    public void testMultipleUsersSignIn() {
        log.info("=== 多用户签到测试开始 ===");

        // 模拟多个用户签到
        for (int i = 1; i <= 5; i++) {
            Long userId = 1000L + i;
            String today = DateUtil.getTodayString();

            String result = signInService.signIn(userId, today);
            log.info("用户{}签到结果: {}", userId, result);

            // 查询连续签到天数
            int consecutiveDays = signInService.getConsecutiveSignInDays(userId, today);
            log.info("用户{}连续签到天数: {}", userId, consecutiveDays);
        }

        log.info("=== 多用户签到测试结束 ===");
    }

    @Test
    public void testSignInPerformance() {
        log.info("=== 签到性能测试开始 ===");

        Long userId = 9999L;
        String today = DateUtil.getTodayString();

        long startTime = System.currentTimeMillis();

        // 模拟1000次签到查询
        for (int i = 0; i < 1000; i++) {
            signInService.isSignedIn(userId, today);
        }

        long endTime = System.currentTimeMillis();
        long duration = endTime - startTime;

        log.info("1000次签到状态查询耗时: {}ms", duration);
        log.info("平均每次查询耗时: {}ms", (double) duration / 1000);

        log.info("=== 签到性能测试结束 ===");
    }
} 
