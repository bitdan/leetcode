package com.linger.module.aspect;

import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * @version 1.0
 * @description
 * @date 2025/7/10 10:43:30
 */
@Slf4j
@Aspect
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 1)  // 让事务切面比锁切面优先级稍低
public class TransactionLoggingAspect {

    @Pointcut("@annotation(org.springframework.transaction.annotation.Transactional)")
    public void transactionalPointcut() {
    }

    @Around("transactionalPointcut()")
    public Object around(ProceedingJoinPoint joinPoint) throws Throwable {
        log.info(">>> [Transactional] 事务开始");
        Object result = joinPoint.proceed();
        log.info("<<< [Transactional] 事务结束");
        return result;
    }
}
