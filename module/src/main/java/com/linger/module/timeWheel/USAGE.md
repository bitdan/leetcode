# 时间轮使用示例

## 快速开始

### 1. 基本使用

```java
import com.linger.module.timeWheel.TimeWheelScheduler;

import java.util.concurrent.TimeUnit;

public class BasicExample {
    public static void main(String[] args) throws InterruptedException {
        // 创建调度器
        TimeWheelScheduler scheduler = new TimeWheelScheduler();
        scheduler.start();

        // 延迟执行任务
        scheduler.schedule(1, TimeUnit.SECONDS, () -> {
            System.out.println("1秒后执行的任务");
        });

        // 等待任务执行
        Thread.sleep(2000);

        // 停止调度器
        scheduler.stop();
    }
}
```

### 2. 异步任务

```java
import java.util.concurrent.CompletableFuture;

public class AsyncExample {
    public static void main(String[] args) throws Exception {
        TimeWheelScheduler scheduler = new TimeWheelScheduler();
        scheduler.start();

        // 异步执行任务并获取结果
        CompletableFuture<String> future = scheduler.scheduleAsync(2, TimeUnit.SECONDS, () -> {
            return "异步任务完成";
        });

        // 处理结果
        String result = future.get();
        System.out.println("结果: " + result);

        scheduler.stop();
    }
}
```

### 3. 多个任务

```java
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;

public class MultipleTasksExample {
    public static void main(String[] args) throws InterruptedException {
        TimeWheelScheduler scheduler = new TimeWheelScheduler();
        scheduler.start();

        CountDownLatch latch = new CountDownLatch(3);
        AtomicInteger counter = new AtomicInteger(0);

        // 调度多个任务
        scheduler.schedule(1, TimeUnit.SECONDS, () -> {
            System.out.println("任务1执行");
            counter.incrementAndGet();
            latch.countDown();
        });

        scheduler.schedule(2, TimeUnit.SECONDS, () -> {
            System.out.println("任务2执行");
            counter.incrementAndGet();
            latch.countDown();
        });

        scheduler.schedule(3, TimeUnit.SECONDS, () -> {
            System.out.println("任务3执行");
            counter.incrementAndGet();
            latch.countDown();
        });

        // 等待所有任务完成
        latch.await();
        System.out.println("所有任务完成，计数器: " + counter.get());

        scheduler.stop();
    }
}
```

## 实际应用场景

### 1. 订单超时处理

```java
public class OrderTimeoutExample {
    private final TimeWheelScheduler scheduler;

    public OrderTimeoutExample() {
        this.scheduler = new TimeWheelScheduler();
        this.scheduler.start();
    }

    public void createOrder(String orderId) {
        System.out.println("创建订单: " + orderId);

        // 设置订单超时处理
        scheduler.schedule(30, TimeUnit.MINUTES, () -> {
            System.out.println("订单 " + orderId + " 超时，执行取消操作");
            cancelOrder(orderId);
        });
    }

    private void cancelOrder(String orderId) {
        // 订单取消逻辑
        System.out.println("取消订单: " + orderId);
    }

    public void stop() {
        scheduler.stop();
    }
}
```

### 2. 缓存过期管理

```java
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class CacheExample {
    private final TimeWheelScheduler scheduler;
    private final Map<String, Object> cache;

    public CacheExample() {
        this.scheduler = new TimeWheelScheduler();
        this.cache = new ConcurrentHashMap<>();
        this.scheduler.start();
    }

    public void put(String key, Object value, long ttlSeconds) {
        cache.put(key, value);
        System.out.println("设置缓存: " + key + " = " + value);

        // 设置缓存过期处理
        scheduler.schedule(ttlSeconds, TimeUnit.SECONDS, () -> {
            System.out.println("缓存过期: " + key);
            remove(key);
        });
    }

    private void remove(String key) {
        cache.remove(key);
        System.out.println("移除缓存: " + key);
    }

    public Object get(String key) {
        return cache.get(key);
    }

    public void stop() {
        scheduler.stop();
    }
}
```

### 3. 心跳检测

```java
public class HeartbeatExample {
    private final TimeWheelScheduler scheduler;
    private final String serverId;

    public HeartbeatExample(String serverId) {
        this.scheduler = new TimeWheelScheduler();
        this.serverId = serverId;
        this.scheduler.start();
    }

    public void startHeartbeat() {
        System.out.println("启动心跳检测: " + serverId);

        // 定期发送心跳
        scheduler.schedule(5, TimeUnit.SECONDS, () -> {
            sendHeartbeat();
        });
    }

    private void sendHeartbeat() {
        System.out.println("服务器 " + serverId + " 发送心跳: " + System.currentTimeMillis());
        // 实际的心跳发送逻辑
    }

    public void stop() {
        scheduler.stop();
    }
}
```

### 4. 延迟队列

```java
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;

public class DelayQueueExample {
    private final TimeWheelScheduler scheduler;
    private final BlockingQueue<String> messageQueue;

    public DelayQueueExample() {
        this.scheduler = new TimeWheelScheduler();
        this.messageQueue = new LinkedBlockingQueue<>();
        this.scheduler.start();
    }

    public void sendDelayedMessage(String message, long delayMs) {
        System.out.println("发送延迟消息: " + message + ", 延迟: " + delayMs + "ms");

        // 延迟处理消息
        scheduler.schedule(delayMs, TimeUnit.MILLISECONDS, () -> {
            processMessage(message);
        });
    }

    private void processMessage(String message) {
        System.out.println("处理延迟消息: " + message);
        messageQueue.offer(message);
    }

    public String receiveMessage() throws InterruptedException {
        return messageQueue.take();
    }

    public void stop() {
        scheduler.stop();
    }
}
```

## 高级用法

### 1. 自定义配置

```java
public class CustomConfigExample {
    public static void main(String[] args) {
        // 自定义时间轮参数
        // tickMs: 50ms精度, wheelSize: 200个格子
        TimeWheelScheduler scheduler = new TimeWheelScheduler(50, 200);
        scheduler.start();

        System.out.println("时间轮大小: " + scheduler.getWheelSize());
        System.out.println("时间轮间隔: " + scheduler.getInterval() + "ms");

        // 使用调度器...

        scheduler.stop();
    }
}
```

### 2. 批量任务处理

```java
import java.util.List;
import java.util.ArrayList;

public class BatchTaskExample {
    public static void main(String[] args) throws InterruptedException {
        TimeWheelScheduler scheduler = new TimeWheelScheduler();
        scheduler.start();

        CountDownLatch latch = new CountDownLatch(10);

        // 批量添加任务
        for (int i = 0; i < 10; i++) {
            final int taskId = i;
            scheduler.schedule(100 * (i + 1), TimeUnit.MILLISECONDS, () -> {
                System.out.println("批量任务 " + taskId + " 执行");
                latch.countDown();
            });
        }

        latch.await();
        System.out.println("所有批量任务完成");

        scheduler.stop();
    }
}
```

### 3. 错误处理

```java
public class ErrorHandlingExample {
    public static void main(String[] args) {
        TimeWheelScheduler scheduler = new TimeWheelScheduler();
        scheduler.start();

        // 任务包含错误处理
        scheduler.schedule(1, TimeUnit.SECONDS, () -> {
            try {
                // 可能抛出异常的任务
                riskyTask();
            } catch (Exception e) {
                System.err.println("任务执行异常: " + e.getMessage());
                // 错误处理逻辑
            }
        });

        // 异步任务的错误处理
        scheduler.scheduleAsync(2, TimeUnit.SECONDS, () -> {
            return riskyAsyncTask();
        }).exceptionally(throwable -> {
            System.err.println("异步任务异常: " + throwable.getMessage());
            return "错误处理结果";
        });

        scheduler.stop();
    }

    private static void riskyTask() {
        if (Math.random() > 0.5) {
            throw new RuntimeException("随机异常");
        }
        System.out.println("任务执行成功");
    }

    private static String riskyAsyncTask() {
        if (Math.random() > 0.5) {
            throw new RuntimeException("异步任务随机异常");
        }
        return "异步任务成功";
    }
}
```

## 性能测试示例

```java
import java.util.concurrent.atomic.AtomicLong;

public class PerformanceTestExample {
    public static void main(String[] args) throws InterruptedException {
        TimeWheelScheduler scheduler = new TimeWheelScheduler();
        scheduler.start();

        AtomicLong taskCount = new AtomicLong(0);
        long startTime = System.currentTimeMillis();

        // 添加大量任务
        for (int i = 0; i < 10000; i++) {
            scheduler.schedule(100, TimeUnit.MILLISECONDS, () -> {
                taskCount.incrementAndGet();
            });
        }

        // 等待任务执行
        Thread.sleep(2000);

        long endTime = System.currentTimeMillis();
        System.out.println("执行任务数: " + taskCount.get());
        System.out.println("总耗时: " + (endTime - startTime) + "ms");

        scheduler.stop();
    }
}
```

## 注意事项

1. **资源管理**: 确保在应用关闭时调用 `scheduler.stop()`
2. **异常处理**: 在任务中添加适当的异常处理
3. **参数选择**: 根据实际需求选择合适的 `tickMs` 和 `wheelSize`
4. **内存监控**: 定期检查任务数量，避免内存泄漏
5. **线程安全**: 时间轮本身是线程安全的，但任务执行需要自己保证

这些示例展示了时间轮在各种场景下的使用方法，您可以根据实际需求进行调整和扩展。 
