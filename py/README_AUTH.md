# Tool Hub 认证系统

## 概述

这是一个完整的用户认证系统，包括用户注册、登录、登出、JWT token管理和Redis会话存储。

## 功能特性

- ✅ 用户注册和登录
- ✅ JWT token生成和验证
- ✅ Redis会话存储（6小时过期）
- ✅ 验证码功能
- ✅ 用户信息管理
- ✅ 自动会话延长
- ✅ 安全的密码加密

## 技术栈

- **后端**: FastAPI + Redis + JWT
- **前端**: Vue 3 + TypeScript + Vuetify
- **密码加密**: bcrypt
- **会话存储**: Redis

## 安装和配置

### 1. 安装依赖

```bash
cd py
pip install -r requirements.txt
```

### 2. 配置Redis

编辑 `config.yaml` 文件：

```yaml
redis:
  host: 192.168.9.188
  port: 6379
  database: 14
  password: null

jwt:
  secret_key: "your-secret-key-change-in-production"
  expiration_hours: 6
```

或者通过环境变量配置：

```bash
export REDIS_HOST=192.168.9.188
export REDIS_PORT=6379
export REDIS_DATABASE=14
export JWT_SECRET_KEY=your-secret-key-change-in-production
export JWT_EXPIRATION_HOURS=6
```

### 3. 启动服务

```bash
python start.py
```

服务将在 `http://localhost:8000` 启动。

## API 接口

### 认证接口

#### 获取验证码

```
GET /api/v1/captchaImage
```

#### 用户注册

```
POST /api/v1/register
Content-Type: application/json

{
  "username": "testuser",
  "password": "123456",
  "confirm_password": "123456",
  "code": "验证码",
  "uuid": "验证码UUID",
  "user_type": "sys_user"
}
```

#### 用户登录

```
POST /api/v1/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123",
  "code": "验证码",
  "uuid": "验证码UUID"
}
```

#### 获取用户信息

```
GET /api/v1/getInfo
Authorization: Bearer <token>
```

#### 用户登出

```
POST /api/v1/logout
Authorization: Bearer <token>
```

## 默认账号

系统预设了一个管理员账号：

- 用户名: `admin`
- 密码: `admin123`

## 测试

运行测试脚本：

```bash
python test_auth.py
```

这将测试所有认证功能，包括：

- 获取验证码
- 用户注册
- 用户登录
- 获取用户信息
- 用户登出

## 前端集成

前端已经适配了新的API接口：

1. **API调用**: `tool-hub/src/api/auth.ts`
2. **认证逻辑**: `tool-hub/src/composables/useAuth.ts`
3. **用户状态**: `tool-hub/src/stores/user.ts`
4. **登录页面**: `tool-hub/src/views/auth/LoginView.vue`
5. **注册页面**: `tool-hub/src/views/auth/RegisterView.vue`

## 安全特性

1. **密码加密**: 使用bcrypt加密存储
2. **JWT签名**: 使用HMAC-SHA256算法
3. **会话管理**: Redis存储，自动过期
4. **验证码**: 防止暴力破解
5. **Token验证**: 每次请求验证token有效性

## 配置说明

### Redis配置

- `host`: Redis服务器地址
- `port`: Redis端口
- `database`: Redis数据库索引
- `password`: Redis密码（可选）

### JWT配置

- `secret_key`: JWT签名密钥
- `expiration_hours`: Token过期时间（小时）

## 部署建议

1. **生产环境**:
    - 修改JWT密钥为强密码
    - 配置Redis密码
    - 使用HTTPS
    - 设置合适的CORS策略

2. **监控**:
    - 监控Redis连接状态
    - 监控API响应时间
    - 记录认证失败日志

## 故障排除

### Redis连接失败

1. 检查Redis服务是否运行
2. 验证网络连接
3. 检查配置参数

### Token验证失败

1. 检查JWT密钥配置
2. 验证token格式
3. 检查Redis中的会话数据

### 前端认证失败

1. 检查API地址配置
2. 验证CORS设置
3. 检查token存储

## 扩展功能

可以考虑添加的功能：

- 邮箱验证
- 密码重置
- 多因素认证
- 用户权限管理
- 登录日志
- 会话管理界面
