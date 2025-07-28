# 轻量级时间轮实现

## 概述

这是一个基于时间轮算法的轻量级定时任务调度器实现，支持毫秒级精度的定时任务调度，具有高性能、低延迟、可扩展等特点。

## 核心特性

- ✅ **高性能**: O(1)时间复杂度添加和删除任务
- ✅ **高精度**: 支持毫秒级精度的定时调度
- ✅ **可扩展**: 支持溢出时间轮处理长时间延迟
- ✅ **线程安全**: 使用原子操作和同步机制
- ✅ **易用性**: 提供简洁的API接口
- ✅ **轻量级**: 无外部依赖，纯Java实现

## 架构设计

```
TimeWheelScheduler (调度器)
    ↓
TimeWheel (时间轮核心)
    ↓
TimeWheelBucket[] (时间轮桶数组)
    ↓
TimerTaskList (任务链表)
    ↓
TimerTask (定时任务)
```

### 核心组件

#### 1. TimeWheelScheduler

- **作用**: 提供用户友好的API接口
- **功能**: 管理时间轮生命周期，任务执行调度
- **特性**: 支持同步和异步任务执行

#### 2. TimeWheel

- **作用**: 时间轮核心算法实现
- **功能**: 任务分配、时间推进、溢出处理
- **特性**: 支持层级时间轮结构

#### 3. TimeWheelBucket

- **作用**: 时间轮桶，管理同一时间格子内的任务
- **功能**: 任务存储、过期处理
- **特性**: 实现Delayed接口，支持延迟队列

#### 4. TimerTaskList

- **作用**: 任务链表，管理桶中的任务
- **功能**: 任务添加、删除、遍历
- **特性**: 双向链表，O(1)操作复杂度

#### 5. TimerTask

- **作用**: 定时任务封装
- **功能**: 任务执行、状态管理
- **特性**: 支持任务ID、创建时间跟踪

## 快速开始

### 1. 基本使用

```java
// 创建调度器
TimeWheelScheduler scheduler = new TimeWheelScheduler();
scheduler.

start();

// 延迟执行任务
scheduler.

schedule(1,TimeUnit.SECONDS, () ->{
        System.out.

println("1秒后执行的任务");
});

// 停止调度器
        scheduler.

stop();
```

### 2. 异步任务

```java
// 异步执行任务
CompletableFuture<String> future = scheduler.scheduleAsync(2, TimeUnit.SECONDS, () -> {
            return "异步任务结果";
        });

// 处理结果
future.

thenAccept(result ->{
        System.out.

println("任务结果: "+result);
});
```

### 3. 自定义配置

```java
// 自定义时间轮参数
// tickMs: 100ms精度, wheelSize: 100个格子
TimeWheelScheduler scheduler = new TimeWheelScheduler(100, 100);
scheduler.

start();
```

## API 参考

### TimeWheelScheduler

#### 构造函数

```java
// 默认构造函数 (100ms精度, 100个格子)
TimeWheelScheduler()

// 自定义构造函数
TimeWheelScheduler(long tickMs, int wheelSize)
```

#### 主要方法

```java
// 启动调度器
void start()

// 停止调度器
void stop()

// 延迟执行任务
void schedule(long delay, TimeUnit unit, Runnable task)

// 异步执行任务
CompletableFuture<Void> scheduleAsync(long delay, TimeUnit unit, Runnable task)

// 异步执行任务并返回结果
<T> CompletableFuture<T> scheduleAsync(long delay, TimeUnit unit, Supplier<T> supplier)

// 检查调度器状态
boolean isStarted()

// 获取时间轮信息
long getCurrentTime()

int getWheelSize()

long getInterval()
```

## 算法原理

### 时间轮算法

时间轮是一种高效处理大量定时任务的数据结构，其核心思想是将时间分割成固定大小的格子，每个格子代表一个时间间隔。

#### 任务分配算法

```java
// 计算任务应该放在哪个桶中
long virtualId = (expiration / tickMs);  // 虚拟时间ID
int index = (int) (virtualId % wheelSize);  // 桶索引
```

**示例**:

- 时间轮: 100ms精度，100个格子
- 任务延迟: 500ms
- 计算: virtualId = 500/100 = 5, index = 5%100 = 5
- 结果: 任务放在第5个桶中

#### 溢出时间轮机制

当任务延迟时间超过当前时间轮的 `interval` 时，会创建溢出时间轮：

```
主时间轮 (100ms × 100 = 10秒)
    ↓
溢出时间轮 (10秒 × 100 = 1000秒)
    ↓
更多层级...
```

### 工作流程

#### 1. 任务添加流程

```
用户调用 schedule() 
    ↓
创建 TimerTask
    ↓
TimeWheel.addTask()
    ↓
计算桶索引 (virtualId % wheelSize)
    ↓
添加到对应桶的 TimerTaskList
    ↓
桶添加到 DelayQueue（如果首次添加）
```

#### 2. 任务执行流程

```
定时器触发 run()
    ↓
推进当前时间 advanceClock()
    ↓
从 DelayQueue 取出到期桶
    ↓
桶.flush() 处理所有任务
    ↓
检查任务是否过期
    ↓
过期: 直接执行 task.run()
未过期: 重新添加到时间轮 addTask()
```

## 性能特点

### 时间复杂度

| 操作   | 时间复杂度 | 说明         |
|------|-------|------------|
| 添加任务 | O(1)  | 直接计算桶索引并添加 |
| 删除任务 | O(1)  | 从链表中移除节点   |
| 查找任务 | O(1)  | 通过桶索引直接定位  |
| 执行任务 | O(1)  | 从延迟队列取出桶   |

### 空间复杂度

- **内存占用**: O(n)，n为任务数量
- **桶数量**: 固定大小，不随任务数量增长
- **溢出时间轮**: 按需创建，层级深度有限

### 性能优势

1. **高效**: 相比传统定时器，时间轮算法效率更高
2. **精确**: 支持毫秒级精度的定时调度
3. **可扩展**: 支持溢出时间轮处理长时间延迟
4. **低延迟**: 任务执行延迟最小化

## 使用场景

### 1. 订单超时处理

```java
TimeWheelScheduler scheduler = new TimeWheelScheduler();
scheduler.

start();

// 创建订单时设置超时处理
scheduler.

schedule(30,TimeUnit.MINUTES, () ->{
        // 订单超时，执行取消逻辑
        orderService.

cancelOrder(orderId);
});
```

### 2. 缓存过期管理

```java
// 设置缓存时添加过期处理
scheduler.schedule(ttlSeconds, TimeUnit.SECONDS, () ->{
        // 缓存过期，清理缓存
        cache.

remove(key);
});
```

### 3. 心跳检测

```java
// 定期发送心跳
scheduler.schedule(5,TimeUnit.SECONDS, () ->{
        // 发送心跳包
        heartbeatService.

sendHeartbeat(serverId);
});
```

### 4. 延迟队列

```java
// 实现延迟队列功能
scheduler.schedule(delayMs, TimeUnit.MILLISECONDS, () ->{
        // 延迟消息处理
        messageProcessor.

process(message);
});
```

## 配置建议

### 时间轮参数选择

| 场景    | tickMs | wheelSize | 适用延迟范围 |
|-------|--------|-----------|--------|
| 高频短延迟 | 1ms    | 1000      | 0-1秒   |
| 一般应用  | 100ms  | 100       | 0-10秒  |
| 低频长延迟 | 1秒     | 100       | 0-100秒 |

### 线程池配置

```java
// 自定义线程池大小
TimeWheelScheduler scheduler = new TimeWheelScheduler() {
            @Override
            protected ExecutorService createTaskExecutor() {
                return Executors.newFixedThreadPool(4); // 4个线程
            }
        };
```

## 注意事项

### 1. 内存管理

- 时间轮桶数量固定，内存占用可控
- 任务执行完成后会自动清理
- 建议定期检查任务数量，避免内存泄漏

### 2. 精度考虑

- tickMs越小，精度越高，但CPU占用也越高
- 建议根据实际需求选择合适的精度
- 默认100ms精度适合大多数场景

### 3. 线程安全

- 时间轮内部使用原子操作保证线程安全
- 任务执行在独立线程池中，不会阻塞时间轮线程
- 支持多线程并发添加任务

### 4. 异常处理

- 任务执行异常会被捕获并记录
- 单个任务异常不会影响其他任务执行
- 建议在任务中添加适当的异常处理

## 最佳实践

### 1. 合理设置参数

```java
// 根据业务需求设置合适的参数
TimeWheelScheduler scheduler = new TimeWheelScheduler(
                50,   // 50ms精度，适合需要较高精度的场景
                200   // 200个格子，支持0-10秒的延迟
        );
```

### 2. 资源管理

```java
// 确保在应用关闭时停止调度器
Runtime.getRuntime().

addShutdownHook(new Thread(() ->{
        scheduler.

stop();
}));
```

### 3. 监控和日志

```java
// 添加监控和日志
scheduler.schedule(delay, unit, () ->{
        try{
        // 执行任务
        task.

run();
    }catch(
Exception e){
        logger.

error("任务执行异常",e);
// 添加监控指标
        metrics.

incrementCounter("task.error");
    }
            });
```

### 4. 批量任务处理

```java
// 对于大量相同延迟的任务，可以批量处理
List<Runnable> tasks = getBatchTasks();
for(
Runnable task :tasks){
        scheduler.

schedule(delay, unit, task);
}
```

## 扩展功能

### 1. 任务取消

```java
// 可以通过任务ID实现任务取消功能
class CancellableTask {
    private final int taskId;
    private volatile boolean cancelled = false;

    public void cancel() {
        this.cancelled = true;
    }

    public void run() {
        if (!cancelled) {
            // 执行任务逻辑
        }
    }
}
```

### 2. 任务优先级

```java
// 可以通过任务优先级实现不同的处理策略
class PriorityTask implements Comparable<PriorityTask> {
    private final int priority;
    private final Runnable task;

    @Override
    public int compareTo(PriorityTask other) {
        return Integer.compare(other.priority, this.priority);
    }
}
```

### 3. 任务统计

```java
// 添加任务执行统计功能
class TaskStatistics {
    private final AtomicLong totalTasks = new AtomicLong();
    private final AtomicLong completedTasks = new AtomicLong();
    private final AtomicLong failedTasks = new AtomicLong();

    public void recordTaskExecution(boolean success) {
        if (success) {
            completedTasks.incrementAndGet();
        } else {
            failedTasks.incrementAndGet();
        }
    }
}
```

## 总结

这个轻量级时间轮实现提供了一个高效、可靠、易用的定时任务调度解决方案。通过合理的设计和优化，它能够满足大多数定时任务调度的需求，同时保持良好的性能和可扩展性。

主要优势：

- 🚀 **高性能**: 基于时间轮算法，O(1)操作复杂度
- 🎯 **高精度**: 支持毫秒级精度的定时调度
- 🔧 **易用性**: 简洁的API接口，快速上手
- 🛡️ **可靠性**: 线程安全，异常处理完善
- 📈 **可扩展**: 支持溢出时间轮，处理长时间延迟

无论是简单的延迟任务，还是复杂的定时调度需求，这个时间轮实现都能提供优秀的解决方案。 
