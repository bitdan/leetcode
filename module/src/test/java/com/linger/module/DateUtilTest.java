package com.linger.module;

import com.linger.module.util.DateUtil;
import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.*;

/**
 * DateUtil工具类测试
 */
@Slf4j
public class DateUtilTest {

    @Test
    public void testDateValidation() {
        log.info("=== 测试日期格式验证 ===");

        // 测试有效日期
        assertTrue(DateUtil.isValidDate("2025-01-21"));
        assertTrue(DateUtil.isValidDate("2025-12-31"));
        assertTrue(DateUtil.isValidDate("2024-02-29")); // 闰年

        // 测试无效日期
        assertFalse(DateUtil.isValidDate("2025-13-01")); // 无效月份
        assertFalse(DateUtil.isValidDate("2025-01-32")); // 无效日期
        assertFalse(DateUtil.isValidDate("2025-02-30")); // 2月30日不存在
        assertFalse(DateUtil.isValidDate("2025/01/21")); // 错误格式
        assertFalse(DateUtil.isValidDate("2025-1-21"));  // 缺少前导零
        assertFalse(DateUtil.isValidDate(""));           // 空字符串
        assertFalse(DateUtil.isValidDate(null));        // null值

        log.info("日期格式验证测试通过");
    }

    @Test
    public void testDateParsing() {
        log.info("=== 测试日期解析 ===");

        // 测试正常解析
        LocalDate date1 = DateUtil.parseDate("2025-01-21");
        assertEquals(2025, date1.getYear());
        assertEquals(1, date1.getMonthValue());
        assertEquals(21, date1.getDayOfMonth());

        // 测试异常情况
        assertThrows(IllegalArgumentException.class, () -> {
            DateUtil.parseDate("invalid-date");
        });

        assertThrows(IllegalArgumentException.class, () -> {
            DateUtil.parseDate(null);
        });

        log.info("日期解析测试通过");
    }

    @Test
    public void testDateFormatting() {
        log.info("=== 测试日期格式化 ===");

        LocalDate date = LocalDate.of(2025, 1, 21);
        String formatted = DateUtil.formatDate(date);
        assertEquals("2025-01-21", formatted);

        // 测试null值
        assertNull(DateUtil.formatDate(null));

        log.info("日期格式化测试通过");
    }

    @Test
    public void testDateOperations() {
        log.info("=== 测试日期操作 ===");

        // 测试获取今天、昨天、明天
        String today = DateUtil.getTodayString();
        String yesterday = DateUtil.getYesterdayString();
        String tomorrow = DateUtil.getTomorrowString();

        log.info("今天: {}", today);
        log.info("昨天: {}", yesterday);
        log.info("明天: {}", tomorrow);

        // 测试日期计算
        String result1 = DateUtil.getDaysAfter("2025-01-21", 7);
        assertEquals("2025-01-28", result1);

        String result2 = DateUtil.getDaysBefore("2025-01-21", 7);
        assertEquals("2025-01-14", result2);

        // 测试天数差计算
        long daysBetween = DateUtil.getDaysBetween("2025-01-01", "2025-01-31");
        assertEquals(30, daysBetween);

        log.info("日期操作测试通过");
    }

    @Test
    public void testLeapYear() {
        log.info("=== 测试闰年判断 ===");

        // 测试闰年
        assertTrue(DateUtil.isLeapYear("2024-01-01"));  // 2024是闰年
        assertTrue(DateUtil.isLeapYear("2000-01-01"));  // 2000是闰年

        // 测试非闰年
        assertFalse(DateUtil.isLeapYear("2025-01-01")); // 2025不是闰年
        assertFalse(DateUtil.isLeapYear("2100-01-01")); // 2100不是闰年（世纪年）

        log.info("闰年判断测试通过");
    }

    @Test
    public void testDayOfYear() {
        log.info("=== 测试一年中的第几天 ===");

        // 测试1月1日
        assertEquals(1, DateUtil.getDayOfYear("2025-01-01"));

        // 测试12月31日（非闰年）
        assertEquals(365, DateUtil.getDayOfYear("2025-12-31"));

        // 测试12月31日（闰年）
        assertEquals(366, DateUtil.getDayOfYear("2024-12-31"));

        log.info("一年中的第几天测试通过");
    }

    @Test
    public void testMonthDays() {
        log.info("=== 测试月份天数 ===");

        // 测试不同月份的天数
        assertEquals(31, DateUtil.getDaysInMonth("2025-01")); // 1月
        assertEquals(28, DateUtil.getDaysInMonth("2025-02")); // 2月（非闰年）
        assertEquals(29, DateUtil.getDaysInMonth("2024-02")); // 2月（闰年）
        assertEquals(31, DateUtil.getDaysInMonth("2025-03")); // 3月
        assertEquals(30, DateUtil.getDaysInMonth("2025-04")); // 4月
        assertEquals(31, DateUtil.getDaysInMonth("2025-05")); // 5月
        assertEquals(30, DateUtil.getDaysInMonth("2025-06")); // 6月
        assertEquals(31, DateUtil.getDaysInMonth("2025-07")); // 7月
        assertEquals(31, DateUtil.getDaysInMonth("2025-08")); // 8月
        assertEquals(30, DateUtil.getDaysInMonth("2025-09")); // 9月
        assertEquals(31, DateUtil.getDaysInMonth("2025-10")); // 10月
        assertEquals(30, DateUtil.getDaysInMonth("2025-11")); // 11月
        assertEquals(31, DateUtil.getDaysInMonth("2025-12")); // 12月

        log.info("月份天数测试通过");
    }

    @Test
    public void testDateComparison() {
        log.info("=== 测试日期比较 ===");

        String today = DateUtil.getTodayString();
        String yesterday = DateUtil.getYesterdayString();
        String tomorrow = DateUtil.getTomorrowString();

        // 测试今天判断
        assertTrue(DateUtil.isToday(today));
        assertFalse(DateUtil.isToday(yesterday));
        assertFalse(DateUtil.isToday(tomorrow));

        // 测试昨天判断
        assertTrue(DateUtil.isYesterday(yesterday));
        assertFalse(DateUtil.isYesterday(today));
        assertFalse(DateUtil.isYesterday(tomorrow));

        // 测试明天判断
        assertTrue(DateUtil.isTomorrow(tomorrow));
        assertFalse(DateUtil.isTomorrow(today));
        assertFalse(DateUtil.isTomorrow(yesterday));

        log.info("日期比较测试通过");
    }

    @Test
    public void testCurrentDateInfo() {
        log.info("=== 测试当前日期信息 ===");

        int currentYear = DateUtil.getCurrentYear();
        int currentMonth = DateUtil.getCurrentMonth();
        int currentDay = DateUtil.getCurrentDay();

        log.info("当前年份: {}", currentYear);
        log.info("当前月份: {}", currentMonth);
        log.info("当前日期: {}", currentDay);

        // 验证年份范围合理
        assertTrue(currentYear >= 2020 && currentYear <= 2030);
        assertTrue(currentMonth >= 1 && currentMonth <= 12);
        assertTrue(currentDay >= 1 && currentDay <= 31);

        log.info("当前日期信息测试通过");
    }
} 
