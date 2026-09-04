package com.linger.module.groupbuy.transaction;

import com.linger.module.groupbuy.config.GroupBuyDataSourceProperties;
import com.linger.module.groupbuy.config.GroupBuyTransactionConfiguration;
import com.zaxxer.hikari.HikariDataSource;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * GroupBuyTransactionConfiguration 测试类
 *
 * 其中最关键的是确保 %40 能正确解码成 @。这正好覆盖你本地配置使用的密码形式。
 */
class GroupBuyTransactionConfigurationTest {

    @Test
    void shouldConvertPythonPostgresDsnToJdbcConfiguration() {
        GroupBuyDataSourceProperties properties = new GroupBuyDataSourceProperties();
        properties.setPostgresDsn("postgresql://demo:p%40ss@127.0.0.1:5433/tool_hub?sslmode=disable");
        GroupBuyTransactionConfiguration configuration = new GroupBuyTransactionConfiguration();

        try (HikariDataSource dataSource = configuration.groupBuyDataSource(properties)) {
            assertEquals("jdbc:postgresql://127.0.0.1:5433/tool_hub?sslmode=disable", dataSource.getJdbcUrl());
            assertEquals("demo", dataSource.getUsername());
            assertEquals("p@ss", dataSource.getPassword());
        }
    }
}

