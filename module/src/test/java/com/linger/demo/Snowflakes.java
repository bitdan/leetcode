package com.linger.demo;

import org.junit.jupiter.api.Test;

/**
 * @version 1.0
 * @description Snowflakes
 * @date 2025/8/11 14:35:16
 */
public class Snowflakes {


    @Test
    public void test1111() {

        long id = 1954727443554242560L;

        long sequence = id & 0xFFF; // 取低 12 位
        long workerId = (id >> 12) & 0x1F; // 再右移12位取 5 位
        long datacenterId = (id >> 17) & 0x1F; // 再右移17位取 5 位
        long timestampDiff = (id >> 22) & 0x1FFFFFFFFFFL; // 取高 41 位

        long twepoch = 1288834974657L; // Hutool 默认起始时间
        long actualTimestamp = timestampDiff + twepoch;

        System.out.println("原ID: " + id);
        System.out.println("时间戳差值: " + timestampDiff);
        System.out.println("实际时间: " + new java.util.Date(actualTimestamp));
        System.out.println("数据中心ID: " + datacenterId);
        System.out.println("机器ID: " + workerId);
        System.out.println("序列号: " + sequence);
    }

}
