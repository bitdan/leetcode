package com.linger;

import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.EnumSet;
import java.util.Set;


@Slf4j
public class BusinessDaysCalculator {

    @Test
    public void test() {
        // 定义日期时间格式
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

        // 解析指定的日期时间字符串
        LocalDateTime startTime = LocalDateTime.parse("2024-11-01 15:00:24", formatter);

        // 获取当前日期时间
        LocalDateTime now = LocalDateTime.parse("2024-11-04 15:01:00", formatter);

        boolean exceedBusinessMinutes = this.isExceedBusinessMinutes(startTime, now, 24 * 60);
        log.info("exceedBusinessMinutes is : {}", exceedBusinessMinutes);
    }

    private static final Set<DayOfWeek> WEEKENDS = EnumSet.of(DayOfWeek.SATURDAY, DayOfWeek.SUNDAY);

    /**
     * 计算两个日期之间的工作日分钟数（不包括周末）
     *
     * @param startTime 开始时间
     * @param endTime   结束时间
     * @return 工作日分钟数
     */
    public static long calculateBusinessMinutes(LocalDateTime startTime, LocalDateTime endTime) {
        if (startTime.isAfter(endTime)) {
            throw new IllegalArgumentException("开始时间不能晚于结束时间");
        }

        // 1. 如果是同一天，直接计算分钟差
        if (startTime.toLocalDate().equals(endTime.toLocalDate())) {
            return isWeekend(startTime.getDayOfWeek()) ? 0 :
                ChronoUnit.MINUTES.between(startTime, endTime);
        }

        // 2. 计算完整的工作日天数
        long totalMinutes = calculateCompleteBusinessDays(
            startTime.toLocalDate().plusDays(1),
            endTime.toLocalDate()) * 24 * 60;

        // 3. 添加第一天的分钟数（如果不是周末）
        if (!isWeekend(startTime.getDayOfWeek())) {
            totalMinutes += ChronoUnit.MINUTES.between(
                startTime,
                startTime.toLocalDate().plusDays(1).atStartOfDay()
            );
        }

        // 4. 添加最后一天的分钟数（如果不是周末）
        if (!isWeekend(endTime.getDayOfWeek())) {
            totalMinutes += ChronoUnit.MINUTES.between(
                endTime.toLocalDate().atStartOfDay(),
                endTime
            );
        }
        log.info("totalMinutes is : {}", totalMinutes);
        return totalMinutes;
    }

    /**
     * 计算两个日期之间的完整工作日天数（不包括开始日期和结束日期）
     */
    private static long calculateCompleteBusinessDays(LocalDate startDate, LocalDate endDate) {
        if (startDate.isAfter(endDate)) {
            return 0;
        }

        long totalDays = ChronoUnit.DAYS.between(startDate, endDate);
        long totalWeeks = totalDays / 7;
        long remainingDays = totalDays % 7;

        // 计算完整周的工作日
        long businessDays = totalWeeks * 5;

        // 处理剩余天数
        LocalDate remaining = startDate.plusWeeks(totalWeeks);
        for (int i = 0; i < remainingDays; i++) {
            if (!isWeekend(remaining.plusDays(i).getDayOfWeek())) {
                businessDays++;
            }
        }

        return businessDays;
    }

    /**
     * 检查是否超过指定的工作日分钟数
     *
     * @param startTime 开始时间
     * @param endTime   结束时间
     * @param threshold 阈值（分钟）
     * @return 是否超时
     */
    public static boolean isExceedBusinessMinutes(LocalDateTime startTime, LocalDateTime endTime, long threshold) {
        return calculateBusinessMinutes(startTime, endTime) > threshold;
    }

    /**
     * 判断是否为周末
     */
    private static boolean isWeekend(DayOfWeek dayOfWeek) {
        return WEEKENDS.contains(dayOfWeek);
    }
}
