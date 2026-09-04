package com.linger.module.groupbuy.config;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.OptimisticLockerInnerInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import com.zaxxer.hikari.HikariDataSource;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.util.StringUtils;

import javax.sql.DataSource;
import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.io.UnsupportedEncodingException;

@Configuration
@EnableScheduling
@EnableConfigurationProperties(GroupBuyDataSourceProperties.class)
@MapperScan("com.linger.module.groupbuy.transaction.mapper")
@ConditionalOnProperty(prefix = "groupbuy.transaction", name = "enabled", havingValue = "true")
public class GroupBuyTransactionConfiguration {

    @Bean(destroyMethod = "close")
    public HikariDataSource groupBuyDataSource(GroupBuyDataSourceProperties properties) {
        ParsedDataSource parsed = resolveDataSource(properties);
        if (!StringUtils.hasText(parsed.jdbcUrl)) {
            throw new IllegalStateException("启用拼团交易引擎时必须配置 GROUPBUY_POSTGRES_JDBC_URL 或 POSTGRES_DSN");
        }

        HikariDataSource dataSource = new HikariDataSource();
        dataSource.setPoolName("groupbuy-postgres-pool");
        dataSource.setDriverClassName("org.postgresql.Driver");
        dataSource.setJdbcUrl(parsed.jdbcUrl);
        dataSource.setUsername(parsed.username);
        dataSource.setPassword(parsed.password);
        dataSource.setMaximumPoolSize(properties.getMaximumPoolSize());
        dataSource.setMinimumIdle(properties.getMinimumIdle());
        dataSource.setAutoCommit(true);
        return dataSource;
    }

    @Bean
    public PlatformTransactionManager transactionManager(DataSource groupBuyDataSource) {
        return new DataSourceTransactionManager(groupBuyDataSource);
    }

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        interceptor.addInnerInterceptor(new OptimisticLockerInnerInterceptor());
        interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.POSTGRE_SQL));
        return interceptor;
    }

    private ParsedDataSource resolveDataSource(GroupBuyDataSourceProperties properties) {
        if (StringUtils.hasText(properties.getJdbcUrl())) {
            return new ParsedDataSource(properties.getJdbcUrl(), properties.getUsername(), properties.getPassword());
        }
        if (!StringUtils.hasText(properties.getPostgresDsn())) {
            return new ParsedDataSource(null, null, null);
        }
        try {
            String normalized = properties.getPostgresDsn().replaceFirst("^postgresql\\+[^:]+://", "postgresql://");
            URI uri = URI.create(normalized);
            String rawUserInfo = uri.getRawUserInfo();
            String username = null;
            String password = null;
            if (rawUserInfo != null) {
                String[] parts = rawUserInfo.split(":", 2);
                username = decode(parts[0]);
                password = parts.length > 1 ? decode(parts[1]) : "";
            }
            int port = uri.getPort() < 0 ? 5432 : uri.getPort();
            String jdbcUrl = "jdbc:postgresql://" + uri.getHost() + ":" + port + uri.getRawPath();
            if (StringUtils.hasText(uri.getRawQuery())) {
                jdbcUrl += "?" + uri.getRawQuery();
            }
            return new ParsedDataSource(jdbcUrl, username, password);
        } catch (RuntimeException e) {
            throw new IllegalStateException("POSTGRES_DSN 格式不正确", e);
        }
    }

    private String decode(String value) {
        try {
            return URLDecoder.decode(value, StandardCharsets.UTF_8.name());
        } catch (UnsupportedEncodingException e) {
            throw new IllegalStateException("JVM 不支持 UTF-8", e);
        }
    }

    private static class ParsedDataSource {
        private final String jdbcUrl;
        private final String username;
        private final String password;

        private ParsedDataSource(String jdbcUrl, String username, String password) {
            this.jdbcUrl = jdbcUrl;
            this.username = username;
            this.password = password;
        }
    }
}
