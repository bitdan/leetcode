package com.linger.module.util;

import lombok.extern.slf4j.Slf4j;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;

/**
 * 日期工具类
 *
 * @version 1.0
 * @description 统一处理日期格式转换和验证
 * @date 2025/1/21
 */
@Slf4j
public class DateUtil {

    /**
     * 标准日期格式：yyyy-MM-dd
     */
    public static final String DATE_PATTERN = "yyyy-MM-dd";

    /**
     * 标准日期时间格式：yyyy-MM-dd HH:mm:ss
     */
    public static final String DATETIME_PATTERN = "yyyy-MM-dd HH:mm:ss";

    /**
     * 年月格式：yyyy-MM
     */
    public static final String YEAR_MONTH_PATTERN = "yyyy-MM";

    /**
     * 标准日期格式化器
     */
    public static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern(DATE_PATTERN);

    /**
     * 标准日期时间格式化器
     */
    public static final DateTimeFormatter DATETIME_FORMATTER = DateTimeFormatter.ofPattern(DATETIME_PATTERN);

    /**
     * 年月格式化器
     */
    public static final DateTimeFormatter YEAR_MONTH_FORMATTER = DateTimeFormatter.ofPattern(YEAR_MONTH_PATTERN);

    /**
     * 将字符串转换为LocalDate
     *
     * @param dateStr 日期字符串，格式：yyyy-MM-dd
     * @return LocalDate对象
     * @throws IllegalArgumentException 如果日期格式不正确
     */
    public static LocalDate parseDate(String dateStr) {
        if (dateStr == null || dateStr.trim().isEmpty()) {
            throw new IllegalArgumentException("日期字符串不能为空");
        }

        try {
            return LocalDate.parse(dateStr.trim(), DATE_FORMATTER);
        } catch (DateTimeParseException e) {
            log.error("日期解析失败: {}", dateStr, e);
            throw new IllegalArgumentException("日期格式错误，请使用yyyy-MM-dd格式: " + dateStr);
        }
    }

    /**
     * 将字符串转换为LocalDateTime
     *
     * @param dateTimeStr 日期时间字符串，格式：yyyy-MM-dd HH:mm:ss
     * @return LocalDateTime对象
     * @throws IllegalArgumentException 如果日期时间格式不正确
     */
    public static LocalDateTime parseDateTime(String dateTimeStr) {
        if (dateTimeStr == null || dateTimeStr.trim().isEmpty()) {
            throw new IllegalArgumentException("日期时间字符串不能为空");
        }

        try {
            return LocalDateTime.parse(dateTimeStr.trim(), DATETIME_FORMATTER);
        } catch (DateTimeParseException e) {
            log.error("日期时间解析失败: {}", dateTimeStr, e);
            throw new IllegalArgumentException("日期时间格式错误，请使用yyyy-MM-dd HH:mm:ss格式: " + dateTimeStr);
        }
    }

    /**
     * 将LocalDate转换为字符串
     *
     * @param date LocalDate对象
     * @return 格式化的日期字符串
     */
    public static String formatDate(LocalDate date) {
        if (date == null) {
            return null;
        }
        return date.format(DATE_FORMATTER);
    }

    /**
     * 将LocalDateTime转换为字符串
     *
     * @param dateTime LocalDateTime对象
     * @return 格式化的日期时间字符串
     */
    public static String formatDateTime(LocalDateTime dateTime) {
        if (dateTime == null) {
            return null;
        }
        return dateTime.format(DATETIME_FORMATTER);
    }

    /**
     * 验证日期字符串格式是否正确
     *
     * @param dateStr 日期字符串
     * @return 是否格式正确
     */
    public static boolean isValidDate(String dateStr) {
        if (dateStr == null || dateStr.trim().isEmpty()) {
            return false;
        }

        try {
            LocalDate.parse(dateStr.trim(), DATE_FORMATTER);
            return true;
        } catch (DateTimeParseException e) {
            return false;
        }
    }

    /**
     * 获取今天的日期字符串
     *
     * @return 今天的日期字符串，格式：yyyy-MM-dd
     */
    public static String getTodayString() {
        return formatDate(LocalDate.now());
    }

    /**
     * 获取昨天的日期字符串
     *
     * @return 昨天的日期字符串，格式：yyyy-MM-dd
     */
    public static String getYesterdayString() {
        return formatDate(LocalDate.now().minusDays(1));
    }

    /**
     * 获取明天的日期字符串
     *
     * @return 明天的日期字符串，格式：yyyy-MM-dd
     */
    public static String getTomorrowString() {
        return formatDate(LocalDate.now().plusDays(1));
    }

    /**
     * 获取指定日期前N天的日期字符串
     *
     * @param dateStr 基准日期字符串
     * @param days    天数
     * @return 前N天的日期字符串
     */
    public static String getDaysBefore(String dateStr, long days) {
        LocalDate date = parseDate(dateStr);
        return formatDate(date.minusDays(days));
    }

    /**
     * 获取指定日期后N天的日期字符串
     *
     * @param dateStr 基准日期字符串
     * @param days    天数
     * @return 后N天的日期字符串
     */
    public static String getDaysAfter(String dateStr, long days) {
        LocalDate date = parseDate(dateStr);
        return formatDate(date.plusDays(days));
    }

    /**
     * 计算两个日期之间的天数差
     *
     * @param startDateStr 开始日期字符串
     * @param endDateStr   结束日期字符串
     * @return 天数差
     */
    public static long getDaysBetween(String startDateStr, String endDateStr) {
        LocalDate startDate = parseDate(startDateStr);
        LocalDate endDate = parseDate(endDateStr);
        return java.time.temporal.ChronoUnit.DAYS.between(startDate, endDate);
    }

    /**
     * 判断是否为闰年
     *
     * @param dateStr 日期字符串
     * @return 是否为闰年
     */
    public static boolean isLeapYear(String dateStr) {
        LocalDate date = parseDate(dateStr);
        return date.isLeapYear();
    }

    /**
     * 获取指定日期在一年中的第几天
     *
     * @param dateStr 日期字符串
     * @return 一年中的第几天（1-366）
     */
    public static int getDayOfYear(String dateStr) {
        LocalDate date = parseDate(dateStr);
        return date.getDayOfYear();
    }

    /**
     * 获取指定月份的天数
     *
     * @param yearMonthStr 年月字符串，格式：yyyy-MM
     * @return 该月的天数
     */
    public static int getDaysInMonth(String yearMonthStr) {
        if (yearMonthStr == null || yearMonthStr.trim().isEmpty()) {
            throw new IllegalArgumentException("年月字符串不能为空");
        }

        try {
            LocalDate date = LocalDate.parse(yearMonthStr.trim() + "-01", DATE_FORMATTER);
            return date.lengthOfMonth();
        } catch (DateTimeParseException e) {
            log.error("年月解析失败: {}", yearMonthStr, e);
            throw new IllegalArgumentException("年月格式错误，请使用yyyy-MM格式: " + yearMonthStr);
        }
    }

    /**
     * 获取当前年份
     *
     * @return 当前年份
     */
    public static int getCurrentYear() {
        return LocalDate.now().getYear();
    }

    /**
     * 获取当前月份
     *
     * @return 当前月份
     */
    public static int getCurrentMonth() {
        return LocalDate.now().getMonthValue();
    }

    /**
     * 获取当前日
     *
     * @return 当前日
     */
    public static int getCurrentDay() {
        return LocalDate.now().getDayOfMonth();
    }

    /**
     * 判断是否为今天
     *
     * @param dateStr 日期字符串
     * @return 是否为今天
     */
    public static boolean isToday(String dateStr) {
        LocalDate date = parseDate(dateStr);
        return date.equals(LocalDate.now());
    }

    /**
     * 判断是否为昨天
     *
     * @param dateStr 日期字符串
     * @return 是否为昨天
     */
    public static boolean isYesterday(String dateStr) {
        LocalDate date = parseDate(dateStr);
        return date.equals(LocalDate.now().minusDays(1));
    }

    /**
     * 判断是否为明天
     *
     * @param dateStr 日期字符串
     * @return 是否为明天
     */
    public static boolean isTomorrow(String dateStr) {
        LocalDate date = parseDate(dateStr);
        return date.equals(LocalDate.now().plusDays(1));
    }
} 
