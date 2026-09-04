# 高并发拼团交易引擎

## 1. 能力范围

- PostgreSQL 保存活动、团、订单、成员、库存流水、Outbox 和延迟任务。
- Redis Lua 原子校验活动、个人限购、库存、团名额和重复参团。
- `(user_id, request_id)` 与 Redis 幂等 key 双重防重。
- 支付回调使用订单状态 CAS 和支付流水唯一索引防止重复入账。
- PostgreSQL Outbox 以至少一次方式推进支付确认、库存释放和退款。
- PostgreSQL 延迟任务表负责可靠存储，内存时间轮负责近期任务调度。
- 定时补偿会回收因进程中断而停留在 `INIT` 或过期 `WAIT_PAY` 的订单。

退款网关当前使用 `LocalPaymentGateway` 模拟成功。接入真实支付渠道时，实现 `PaymentGateway`，并以
`paymentNo` 作为退款幂等键。

## 2. 初始化 PostgreSQL

SQL 文件位于同级业务包：

```text
module/src/main/java/com/linger/module/groupbuy/groupbuy_schema.sql
```

PowerShell 示例：

```powershell
psql $env:POSTGRES_DSN -f module/src/main/java/com/linger/module/groupbuy/groupbuy_schema.sql
```

脚本只包含 `CREATE TABLE IF NOT EXISTS` 和索引，不包含测试数据，也不会由应用自动执行。

## 3. 配置并启动

可以直接复用 Python 服务已导出到当前进程的 `POSTGRES_DSN`：

```powershell
$env:GROUPBUY_TRANSACTION_ENABLED="true"
$env:POSTGRES_DSN="postgresql://user:password@host:5432/tool_hub"
mvn -pl module -am -Plocal spring-boot:run
```

也可以配置标准 JDBC 参数：

```powershell
$env:GROUPBUY_TRANSACTION_ENABLED="true"
$env:GROUPBUY_POSTGRES_JDBC_URL="jdbc:postgresql://host:5432/tool_hub"
$env:GROUPBUY_POSTGRES_USERNAME="user"
$env:GROUPBUY_POSTGRES_PASSWORD="password"
mvn -pl module -am -Plocal spring-boot:run
```

交易引擎默认关闭。这样没有 PostgreSQL 配置时，原有 Redis、PDF、TOTP 等功能和测试不会受影响。

## 4. 调用顺序

### 创建活动

```http
POST /api/v1/groupbuy/activities
Content-Type: application/json

{
  "name": "三人拼团",
  "skuId": "SKU-1001",
  "unitPrice": 99.90,
  "totalStock": 1000,
  "perUserLimit": 1,
  "targetCount": 3,
  "payTimeoutSeconds": 300,
  "groupTimeoutSeconds": 3600,
  "startsAt": "2026-09-04T08:00:00Z",
  "endsAt": "2026-09-05T08:00:00Z"
}
```

### 发布活动并开团

```http
POST /api/v1/groupbuy/activities/{activityId}/publish
POST /api/v1/groupbuy/activities/{activityId}/groups

{"creatorUserId": 10001}
```

### 下单

```http
POST /api/v1/groupbuy/orders
Content-Type: application/json

{
  "requestId": "client-request-0001",
  "userId": 10001,
  "activityId": 1,
  "groupId": 1,
  "quantity": 1
}
```

### 支付回调

```http
POST /api/v1/groupbuy/payments/callback
Content-Type: application/json

{
  "orderId": "下单返回的订单ID",
  "paymentNo": "payment-0001",
  "paidAmount": 99.90,
  "paidAt": "2026-09-04T08:10:00Z"
}
```

查询订单：

```http
GET /api/v1/groupbuy/orders/{orderId}
```

## 5. 一致性边界

Redis 是高并发准入层，PostgreSQL 是最终业务事实。系统不声明跨存储 Exactly Once，而是使用：

```text
Lua 原子预占 + 数据库唯一约束 + 状态 CAS + Outbox 至少一次投递 + 幂等消费 + 定时对账
```

库存应满足：

```text
initialStock = available + reserved + confirmed
```

建议压测时同时校验数据库库存流水、Redis 三段库存、团人数和订单状态，不能只统计 HTTP 成功数。

