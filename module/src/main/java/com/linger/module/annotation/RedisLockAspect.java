package com.linger.module.annotation;


import com.linger.module.util.LogFilterUtils;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.redisson.RedissonMultiLock;
import org.redisson.api.RBucket;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.expression.EvaluationContext;
import org.springframework.expression.Expression;
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.lang.reflect.Array;
import java.lang.reflect.Method;
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

    private final String prompt = "请不要重复点击!";
    private final String lock = "lock:";

    @Around("@annotation(redisLock)")
    public Object around(ProceedingJoinPoint joinPoint, RedisLock redisLock) throws Throwable {
        List<String> keys = parseKeys(joinPoint, redisLock);
        String promptMessage = parsePrompt(joinPoint, redisLock);

        if (keys.isEmpty()) {
            return joinPoint.proceed();
        }

        if (redisLock.interval() > 0) {
            boolean allow = checkRequestInterval(keys.get(0), redisLock.interval(), TimeUnit.SECONDS);
            if (!allow) {
                log.warn("请求过于频繁 [{}]: {}", keys, promptMessage);
                throw new Exception(promptMessage);
            }
        }

        List<RLock> locks = keys.stream()
                .map(redissonClient::getLock)
                .collect(Collectors.toList());

        RLock multiLock = new RedissonMultiLock(locks.toArray(new RLock[0]));

        boolean locked = false;
        try {
            locked = multiLock.tryLock(0, -1, TimeUnit.SECONDS);
            if (!locked) {
                log.warn("请求重复 [{}]: {}", keys, promptMessage);
                throw new Exception(promptMessage);
            }

            return joinPoint.proceed();
        } finally {
            if (locked) {
                try {
                    multiLock.unlock();
                } catch (IllegalMonitorStateException e) {
                    log.warn("锁已被自动释放或未持有锁: {}", keys, e);
                } catch (Exception e) {
                    log.error("释放锁异常: {}", keys, e);
                }
            }
        }
    }

    private boolean checkRequestInterval(String key, long interval, TimeUnit unit) {
        String intervalKey = key + ":interval";
        RBucket<String> bucket = redissonClient.getBucket(intervalKey);
        return bucket.trySet("1", interval, unit);
    }


    private List<String> parseKeys(ProceedingJoinPoint joinPoint, RedisLock redisLock) {
        String baseKey = getDefaultKey(joinPoint);

        if (redisLock.key().isEmpty()) {
            return Collections.singletonList(baseKey);
        }

        try {
            EvaluationContext context = buildEvaluationContext(joinPoint);
            ExpressionParser parser = new SpelExpressionParser();
            Expression expression = parser.parseExpression(redisLock.key());
            Object value = expression.getValue(context);

            if (value == null) {
                return Collections.emptyList();
            }

            if (value instanceof Collection) {
                Collection<?> coll = (Collection<?>) value;
                if (coll.isEmpty()) {
                    return Collections.emptyList();
                }
                return coll.stream()
                        .map(v -> getBaseKeyWithoutArgs(joinPoint) + ":" + v)
                        .collect(Collectors.toList());
            } else if (value.getClass().isArray()) {
                int length = Array.getLength(value);
                if (length == 0) {
                    return Collections.emptyList();
                }
                List<String> keys = new ArrayList<>(length);
                for (int i = 0; i < length; i++) {
                    Object element = Array.get(value, i);
                    keys.add(getBaseKeyWithoutArgs(joinPoint) + ":" + element);
                }
                return keys;
            } else {
                return Collections.singletonList(
                        getBaseKeyWithoutArgs(joinPoint) + ":" + value
                );
            }
        } catch (Exception e) {
            log.warn("解析 RedisLock key 失败, 使用默认值: {}", redisLock.key(), e);
            return Collections.singletonList(baseKey);
        }
    }

    /**
     * 默认key格式: lock:类名:方法名:参数值...
     */
    private String getDefaultKey(ProceedingJoinPoint joinPoint) {
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        Method method = signature.getMethod();
        String methodName = method.getName();
        String className = joinPoint.getTarget().getClass().getSimpleName();

        StringBuilder sb = new StringBuilder();
        sb.append(className).append(":").append(methodName);

        Object[] args = joinPoint.getArgs();
        for (Object arg : args) {
            if (LogFilterUtils.isNonLoggable(arg)) continue;
            sb.append(":").append(arg);
        }

        return lock + sb;
    }

    private String getBaseKeyWithoutArgs(ProceedingJoinPoint joinPoint) {
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        Method method = signature.getMethod();
        String methodName = method.getName();
        String className = joinPoint.getTarget().getClass().getSimpleName();
        return lock + className + ":" + methodName;
    }


    private String parsePrompt(ProceedingJoinPoint joinPoint, RedisLock redisLock) {
        String promptExpression = redisLock.prompt();
        if (promptExpression.isEmpty()) {
            return prompt;
        }

        try {
            EvaluationContext context = buildEvaluationContext(joinPoint);
            ExpressionParser parser = new SpelExpressionParser();
            Expression expression = parser.parseExpression(promptExpression);

            // 直接返回解析结果（支持 String 类型）
            return expression.getValue(context, String.class);
        } catch (Exception e) {
            log.warn("RedisLock prompt 解析失败: {}", promptExpression, e);
            return prompt; // 降级为默认提示
        }
    }


    private EvaluationContext buildEvaluationContext(ProceedingJoinPoint joinPoint) {
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        String[] paramNames = signature.getParameterNames();
        Object[] args = joinPoint.getArgs();
        EvaluationContext context = new StandardEvaluationContext();
        for (int i = 0; i < args.length; i++) {
            context.setVariable(paramNames[i], args[i]);
        }
        return context;
    }
}
