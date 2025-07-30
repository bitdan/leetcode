# TOTP 双因素认证系统

基于 `TotpNative` 实现的完整 TOTP（基于时间的一次性密码）双因素认证系统，使用 Redisson 进行数据存储。

## 功能特性

- ✅ 生成 TOTP 密钥（Base32 编码）
- ✅ 验证 TOTP 码（6位数字）
- ✅ 备用码支持（紧急情况使用）
- ✅ 用户锁定机制（防止暴力破解）
- ✅ 完整的用户生命周期管理
- ✅ RESTful API 接口
- ✅ Redis 数据持久化

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   TotpController│    │   TotpService   │    │   TotpNative    │
│   (REST API)    │───▶│   (业务逻辑)     │───▶│   (核心算法)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Redisson      │
                       │   (数据存储)     │
                       └─────────────────┘
```

## API 接口

### 1. 生成 TOTP 密钥

```http
POST /api/totp/generate/{userId}
```

**响应示例：**

```json
{
  "success": true,
  "message": "TOTP密钥生成成功",
  "data": {
    "secretKey": "JBSWY3DPEHPK3PXP",
    "backupCodes": ["12345678", "87654321", ...],
    "qrCodeUrl": "otpauth://totp/MyApp:userId?secret=JBSWY3DPEHPK3PXP&issuer=MyApp"
  }
}
```

### 2. 验证 TOTP 码

```http
POST /api/totp/verify
Content-Type: application/json

{
  "userId": "user123",
  "totpCode": "123456"
}
```

### 3. 启用 TOTP

```http
POST /api/totp/enable
Content-Type: application/json

{
  "userId": "user123",
  "totpCode": "123456"
}
```

### 4. 禁用 TOTP

```http
POST /api/totp/disable/{userId}
```

### 5. 获取用户信息

```http
GET /api/totp/info/{userId}
```

### 6. 删除 TOTP 配置

```http
DELETE /api/totp/delete/{userId}
```

## 使用流程

### 1. 初始化 TOTP

1. 调用 `/api/totp/generate/{userId}` 生成密钥
2. 将 `qrCodeUrl` 提供给用户扫描（使用 Google Authenticator 等应用）
3. 用户输入验证码，调用 `/api/totp/enable` 启用 TOTP

### 2. 日常验证

1. 用户从认证器应用获取 6 位验证码
2. 调用 `/api/totp/verify` 验证码

### 3. 备用码使用

- 当用户无法使用认证器时，可以使用备用码
- 备用码使用后立即失效
- 建议用户安全保存备用码

## 安全特性

### 1. 防暴力破解

- 最大尝试次数：5 次
- 锁定时间：15 分钟
- 自动重置尝试次数

### 2. 数据安全

- 密钥使用 Base32 编码存储
- 敏感信息不通过 API 返回
- 备用码使用后立即删除

### 3. 时间窗口

- TOTP 码有效期：30 秒
- 基于 RFC 6238 标准实现

## 配置参数

在 `TotpService` 中可以调整以下参数：

```java
// 验证码有效期（秒）
private static final int TOTP_VALIDITY_PERIOD = 30;

// 最大尝试次数
private static final int MAX_ATTEMPTS = 5;

// 尝试次数重置时间（分钟）
private static final int ATTEMPT_RESET_MINUTES = 15;

// 备用码数量
private static final int BACKUP_CODES_COUNT = 10;
```

## Redis 数据结构

### 用户数据

- Key: `totp:users`
- Type: Hash
- Field: userId
- Value: TotpUser 对象

### 尝试次数

- Key: `totp:attempts`
- Type: Hash
- Field: userId
- Value: 尝试次数（带过期时间）

### 备用码

- Key: `totp:backup_codes`
- Type: Hash
- Field: backupCode
- Value: userId

## 测试

运行测试类 `TotpServiceTest` 验证系统功能：

```bash
mvn test -Dtest=TotpServiceTest
```

## 集成示例

### 前端集成

```javascript
// 生成 TOTP
async function generateTotp(userId) {
  const response = await fetch(`/api/totp/generate/${userId}`, {
    method: 'POST'
  });
  const result = await response.json();
  
  if (result.success) {
    // 显示二维码
    showQRCode(result.data.qrCodeUrl);
    // 保存备用码
    saveBackupCodes(result.data.backupCodes);
  }
}

// 验证 TOTP
async function verifyTotp(userId, totpCode) {
  const response = await fetch('/api/totp/verify', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ userId, totpCode })
  });
  
  const result = await response.json();
  return result.success;
}
```

### 移动端集成

1. 用户扫描二维码添加到 Google Authenticator
2. 应用自动生成 6 位验证码
3. 用户输入验证码完成验证

## 注意事项

1. **密钥安全**：生成密钥后应通过安全渠道传递给用户
2. **备用码管理**：备用码应安全保存，使用后立即失效
3. **时间同步**：确保服务器时间准确，避免验证失败
4. **用户体验**：提供清晰的错误提示和操作指引
5. **监控告警**：监控验证失败次数，及时发现异常

## 扩展功能

可以考虑添加以下功能：

- [ ] 支持多种 TOTP 算法（SHA256, SHA512）
- [ ] 支持自定义时间窗口
- [ ] 支持多设备管理
- [ ] 支持批量操作
- [ ] 支持审计日志
- [ ] 支持 Webhook 通知 
