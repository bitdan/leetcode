package com.linger.module.aspect;

import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * @version 1.0
 * @description Lock4jLoggingAspect
 * @date 2025/7/10 09:52:42
 */
@Slf4j
@Aspect
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class Lock4jLoggingAspect {

    @Pointcut("@annotation(com.baomidou.lock.annotation.Lock4j)")
    public void lockPointcut() {
    }

    @Around("lockPointcut()")
    public Object around(ProceedingJoinPoint joinPoint) throws Throwable {
        log.info("🔐 Lock4j 切面执行前，是否存在事务: {}", TransactionSynchronizationManager.isActualTransactionActive());
        log.info(">>> [Lock4j] 分布式锁开始");
        Object result = joinPoint.proceed();
        log.info("<<< [Lock4j] 分布式锁结束");
        return result;
    }
}
