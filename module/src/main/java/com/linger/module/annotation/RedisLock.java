package com.linger.module.annotation;


import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * @description RedisLock
 * @date 2025/12/11 18:18:09
 * @version 1.0
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface RedisLock {

    // SpEL表达式，如 "#pdavo.purchaseOrderNumber"
    String key() default "";

    // 间隔单位秒
    long interval() default 5;

    String prompt() default "";

}
