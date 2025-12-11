package com.linger.module.annotation;


import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.redisson.RedissonMultiLock;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.expression.Expression;
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.lang.reflect.Array;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;


@Aspect
@Component
@Slf4j
@Order(Ordered.HIGHEST_PRECEDENCE + 10)
public class RedisLockAspect {

    @Resource
    private RedissonClient redissonClient;

    private static final String DEFAULT_PROMPT = "请不要重复操作！";
    private static final String LOCK_PREFIX = "lock:";

    @Around("@annotation(redisLock)")
    public Object around(ProceedingJoinPoint joinPoint, RedisLock redisLock) throws Throwable {

        List<String> keys = buildKeys(joinPoint, redisLock);
        if (keys.isEmpty()) {
            return joinPoint.proceed();
        }

        String prompt = resolvePrompt(joinPoint, redisLock);

        // interval 限流检查
        checkInterval(keys.get(0), redisLock, prompt);

        RLock multiLock = buildMultiLock(keys);

        boolean locked = false;
        try {
            locked = multiLock.tryLock(2, -1, TimeUnit.SECONDS);
            if (!locked) {
                throw new Exception(prompt);
            }
            return joinPoint.proceed();
        } finally {
            safeUnlock(multiLock, keys);
        }
    }

    /** 解析 SpEL 并构建锁 key */
    private List<String> buildKeys(ProceedingJoinPoint joinPoint, RedisLock redisLock) {
        String baseKey = LOCK_PREFIX + getBaseKey(joinPoint);

        if (redisLock.key().isEmpty()) {
            return Collections.singletonList(baseKey);
        }

        try {
            Object value = parseSpEL(joinPoint, redisLock.key());
            if (value == null) {
                return Collections.emptyList();
            }

            if (value instanceof Collection<?>) {
                return ((Collection<?>) value)
                        .stream()
                        .map(v -> baseKey + ":" + v)
                        .collect(Collectors.toList());
            }

            if (value.getClass().isArray()) {
                List<String> keys = new ArrayList<>();
                int length = Array.getLength(value);
                for (int i = 0; i < length; i++) {
                    keys.add(baseKey + ":" + Array.get(value, i));
                }
                return keys;
            }

            return Collections.singletonList(baseKey + ":" + value);

        } catch (Exception e) {
            log.warn("解析 SpEL key 失败，将使用默认 key，expr={}", redisLock.key(), e);
            return Collections.singletonList(baseKey);
        }
    }

    /** 多锁 */
    private RLock buildMultiLock(List<String> keys) {
        List<RLock> lockList = keys.stream()
                .map(redissonClient::getLock)
                .collect(Collectors.toList());
        return new RedissonMultiLock(lockList.toArray(new RLock[0]));
    }

    /** safe unlock */
    private void safeUnlock(RLock multiLock, List<String> keys) {
        try {
            multiLock.unlock();
        } catch (IllegalMonitorStateException e) {
            log.warn("锁未持有或已自动释放: {}", keys);
        } catch (Throwable t) {
            log.error("释放锁异常 key={}", keys, t);
        }
    }

    /** 限制点击频率 */
    private void checkInterval(String key, RedisLock redisLock, String prompt) throws Exception {
        if (redisLock.interval() <= 0) {
            return;
        }

        String intervalKey = key + ":interval";
        boolean ok = redissonClient.getBucket(intervalKey)
                .trySet("1", redisLock.interval(), TimeUnit.SECONDS);

        if (!ok) {
            throw new Exception(prompt);
        }
    }

    /** 提示语解析 */
    private String resolvePrompt(ProceedingJoinPoint joinPoint, RedisLock redisLock) {
        if (redisLock.prompt().isEmpty()) {
            return DEFAULT_PROMPT;
        }

        try {
            return parseSpEL(joinPoint, redisLock.prompt()).toString();
        } catch (Exception e) {
            return DEFAULT_PROMPT;
        }
    }

    /** SpEL 工具 */
    private Object parseSpEL(ProceedingJoinPoint joinPoint, String expression) {
        ExpressionParser parser = new SpelExpressionParser();
        Expression exp = parser.parseExpression(expression);

        MethodSignature sig = (MethodSignature) joinPoint.getSignature();
        String[] paramNames = sig.getParameterNames();
        Object[] args = joinPoint.getArgs();

        StandardEvaluationContext context = new StandardEvaluationContext();
        for (int i = 0; i < args.length; i++) {
            context.setVariable(paramNames[i], args[i]);
        }
        return exp.getValue(context);
    }

    /** class:method */
    private String getBaseKey(ProceedingJoinPoint joinPoint) {
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        return joinPoint.getTarget().getClass().getSimpleName() + ":" + signature.getMethod().getName();
    }
}
