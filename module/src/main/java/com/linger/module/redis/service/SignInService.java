package com.linger.module.redis.service;

import com.linger.module.util.DateUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RBitSet;
import org.redisson.api.RedissonClient;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;

/**
 * 基于Bitmap的签到统计服务
 *
 * @version 1.0
 * @description 用户签到统计功能
 * @date 2025/1/21
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class SignInService {

    private final RedissonClient redissonClient;

    /**
     * 用户签到
     *
     * @param userId 用户ID
     * @param date   签到日期，格式：yyyy-MM-dd
     * @return 签到结果
     */
    public String signIn(Long userId, String date) {
        try {
            // 验证日期格式
            if (!DateUtil.isValidDate(date)) {
                return "日期格式错误，请使用" + DateUtil.DATE_PATTERN + "格式";
            }
            
            String key = getSignInKey(userId, date);
            RBitSet bitSet = redissonClient.getBitSet(key);

            // 计算日期在一年中的第几天（0-364）
            int dayOfYear = DateUtil.getDayOfYear(date) - 1; // 转换为0-364

            // 检查是否已经签到
            if (bitSet.get(dayOfYear)) {
                return "今日已签到，请明天再来";
            }

            // 执行签到
            bitSet.set(dayOfYear);

            // 设置过期时间（一年后过期）
            bitSet.expire(365, TimeUnit.DAYS);

            return "签到成功！";
        } catch (Exception e) {
            log.error("签到异常，userId: {}, date: {}", userId, date, e);
            return "签到失败：" + e.getMessage();
        }
    }

    /**
     * 查询用户指定日期的签到状态
     *
     * @param userId 用户ID
     * @param date   查询日期，格式：yyyy-MM-dd
     * @return 是否已签到
     */
    public boolean isSignedIn(Long userId, String date) {
        try {
            if (!DateUtil.isValidDate(date)) {
                return false;
            }
            
            String key = getSignInKey(userId, date);
            RBitSet bitSet = redissonClient.getBitSet(key);
            int dayOfYear = DateUtil.getDayOfYear(date) - 1; // 转换为0-364
            return bitSet.get(dayOfYear);
        } catch (Exception e) {
            log.error("查询签到状态异常，userId: {}, date: {}", userId, date, e);
            return false;
        }
    }

    /**
     * 获取用户连续签到天数
     *
     * @param userId 用户ID
     * @param date   查询日期，格式：yyyy-MM-dd
     * @return 连续签到天数
     */
    public int getConsecutiveSignInDays(Long userId, String date) {
        try {
            if (!DateUtil.isValidDate(date)) {
                return 0;
            }
            
            String key = getSignInKey(userId, date);
            RBitSet bitSet = redissonClient.getBitSet(key);

            int currentDayOfYear = DateUtil.getDayOfYear(date) - 1; // 转换为0-364
            int consecutiveDays = 0;

            // 从当前日期往前查找连续签到天数
            for (int i = currentDayOfYear; i >= 0; i--) {
                if (bitSet.get(i)) {
                    consecutiveDays++;
                } else {
                    break;
                }
            }

            // 如果当前日期之前没有签到记录，检查上一年
            if (consecutiveDays == 0) {
                String lastYearKey = getSignInKey(userId, DateUtil.getDaysBefore(date, 365));
                RBitSet lastYearBitSet = redissonClient.getBitSet(lastYearKey);

                // 检查上一年最后几天的签到情况
                for (int i = 364; i >= 0; i--) {
                    if (lastYearBitSet.get(i)) {
                        consecutiveDays++;
                    } else {
                        break;
                    }
                }
            }

            return consecutiveDays;
        } catch (Exception e) {
            log.error("查询连续签到天数异常，userId: {}, date: {}", userId, date, e);
            return 0;
        }
    }

    /**
     * 获取用户指定月份的签到统计
     *
     * @param userId    用户ID
     * @param yearMonth 年月，格式：yyyy-MM
     * @return 签到统计信息
     */
    public String getMonthlySignInStats(Long userId, String yearMonth) {
        try {
            int totalDays = DateUtil.getDaysInMonth(yearMonth);
            int signedDays = 0;

            for (int day = 1; day <= totalDays; day++) {
                String date = String.format("%s-%02d", yearMonth, day);
                if (isSignedIn(userId, date)) {
                    signedDays++;
                }
            }

            double signInRate = totalDays > 0 ? (double) signedDays / totalDays * 100 : 0;

            return String.format("用户%d在%s月份签到统计：总天数%d天，已签到%d天，签到率%.1f%%",
                    userId, yearMonth, totalDays, signedDays, signInRate);
        } catch (Exception e) {
            log.error("查询月度签到统计异常，userId: {}, yearMonth: {}", userId, yearMonth, e);
            return "查询失败：" + e.getMessage();
        }
    }

    /**
     * 获取用户指定年份的签到统计
     *
     * @param userId 用户ID
     * @param year   年份
     * @return 签到统计信息
     */
    public String getYearlySignInStats(Long userId, int year) {
        try {
            String yearStr = String.valueOf(year);
            int totalDays = DateUtil.isLeapYear(yearStr + "-01-01") ? 366 : 365;
            int signedDays = 0;

            String key = getSignInKey(userId, year + "-01-01");
            RBitSet bitSet = redissonClient.getBitSet(key);

            for (int day = 0; day < totalDays; day++) {
                if (bitSet.get(day)) {
                    signedDays++;
                }
            }

            double signInRate = (double) signedDays / totalDays * 100;

            return String.format("用户%d在%d年签到统计：总天数%d天，已签到%d天，签到率%.1f%%",
                    userId, year, totalDays, signedDays, signInRate);
        } catch (Exception e) {
            log.error("查询年度签到统计异常，userId: {}, year: {}", userId, year, e);
            return "查询失败：" + e.getMessage();
        }
    }

    /**
     * 批量查询用户签到状态（用于日历展示）
     *
     * @param userId    用户ID
     * @param startDate 开始日期，格式：yyyy-MM-dd
     * @param endDate   结束日期，格式：yyyy-MM-dd
     * @return 签到状态映射
     */
    public String getSignInStatusRange(Long userId, String startDate, String endDate) {
        try {
            // 验证日期格式
            if (!DateUtil.isValidDate(startDate) || !DateUtil.isValidDate(endDate)) {
                return "日期格式错误，请使用" + DateUtil.DATE_PATTERN + "格式";
            }
            
            StringBuilder result = new StringBuilder();
            result.append(String.format("用户%d从%s到%s的签到记录：\n", userId, startDate, endDate));

            // 这里简化处理，实际项目中可以使用更高效的批量查询
            String currentDate = startDate;
            while (!currentDate.equals(endDate)) {
                boolean signed = isSignedIn(userId, currentDate);
                result.append(String.format("%s: %s\n", currentDate, signed ? "已签到" : "未签到"));
                currentDate = DateUtil.getDaysAfter(currentDate, 1);
            }

            // 处理最后一天
            boolean signed = isSignedIn(userId, endDate);
            result.append(String.format("%s: %s", endDate, signed ? "已签到" : "未签到"));

            return result.toString();
        } catch (Exception e) {
            log.error("批量查询签到状态异常，userId: {}, startDate: {}, endDate: {}",
                    userId, startDate, endDate, e);
            return "查询失败：" + e.getMessage();
        }
    }

    // ==================== 辅助方法 ====================

    /**
     * 获取签到bitmap的key
     */
    private String getSignInKey(Long userId, String date) {
        String year = date.substring(0, 4);
        return String.format("signin:user:%d:year:%s", userId, year);
    }


} 
