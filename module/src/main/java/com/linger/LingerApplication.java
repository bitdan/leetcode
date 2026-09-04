package com.linger;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.core.env.Environment;

import java.net.InetAddress;
import java.net.UnknownHostException;

/**
 * @version 1.0
 * @description
 * @date 2025/7/10 10:14:35
 */
@Slf4j
/*
 * MyBatis-Plus 和 PostgreSQL 驱动存在时，Spring Boot 会尝试自动创建默认数据源；但拼团交易引擎是可选
 * 模块，未启用或未配置数据库时，自动装配会因缺少 spring.datasource.url 而导致应用启动失败，因此这里
 * 排除 DataSourceAutoConfiguration。启用拼团模块后，GroupBuyTransactionConfiguration 会根据
 * groupbuy.transaction.datasource 配置创建专用 HikariDataSource 和事务管理器，不受此排除项影响。
 * 如果后续项目统一使用 spring.datasource 管理数据库，应移除此排除项并改回 Spring Boot 标准数据源配置。
 *
 *
 * application-local.yml
  → groupbuy.transaction.enabled=true
  → GroupBuyTransactionConfiguration 生效
  → 解析 postgres-dsn
  → 创建 HikariDataSource
  → 创建事务管理器和 MyBatis Mapper
 */
@SpringBootApplication(exclude = DataSourceAutoConfiguration.class)
public class LingerApplication {
    public static void main(String[] args) throws UnknownHostException {
        ConfigurableApplicationContext applicationContext = SpringApplication.run(LingerApplication.class, args);
        Environment env = applicationContext.getEnvironment();
        String ip = InetAddress.getLocalHost().getHostAddress();
        String port = env.getProperty("server.port");
        log.info("\n----------------------------------------------------------\n\t" +
                "Application is running! Access URLs:\n\t" +
                "Local: \t\thttp://localhost:" + port + "/\n\t" +
                "External: \thttp://" + ip + ":" + port + "/\n\t"
        );
    }
}
