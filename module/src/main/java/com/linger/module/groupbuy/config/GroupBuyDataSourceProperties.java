package com.linger.module.groupbuy.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "groupbuy.transaction.datasource")
public class GroupBuyDataSourceProperties {

    private String jdbcUrl;
    private String postgresDsn;
    private String username;
    private String password;
    private int maximumPoolSize = 20;
    private int minimumIdle = 2;
}
