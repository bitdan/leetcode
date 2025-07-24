package com.linger.module.transaction.service;

import com.baomidou.lock.annotation.Lock4j;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * @version 1.0
 * @description QuotationServiceImpl
 * @date 2025/7/10 09:57:07
 */
@Slf4j
@Service
public class QuotationServiceImpl implements QuotationService {

    @Override
    @Lock4j(keys = "#materialSku")
    @Transactional(rollbackFor = Exception.class)
    public void createQuotation(String materialSku) {

        try {
            // 模拟业务耗时
            Thread.sleep(2000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

    }
}
