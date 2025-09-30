# 微信登录功能使用说明

## 功能概述

本模块实现了完整的微信登录功能，包括：

1. **微信网页授权登录** - 通过微信开放平台进行网页授权登录
2. **微信扫码登录** - 生成二维码供用户扫码登录
3. **微信账号绑定** - 将微信账号与现有用户账号绑定
4. **微信用户管理** - 管理微信用户信息和登录状态

## 配置说明

### 环境变量配置

在启动应用前，需要设置以下环境变量：

```bash
# 微信开放平台配置
export WECHAT_APP_ID="your_wechat_app_id"
export WECHAT_APP_SECRET="your_wechat_app_secret"

# 回调地址配置
export WECHAT_REDIRECT_URI="http://your-domain.com/api/v1/wechat/callback"
export FRONTEND_DOMAIN="http://your-frontend-domain.com"

# 二维码配置（可选）
export QR_EXPIRE_TIME="300"  # 二维码过期时间（秒），默认5分钟
export QR_SIZE="300"  # 二维码大小，默认300px
```

### 微信开放平台配置

1. 在微信开放平台注册应用
2. 获取 AppID 和 AppSecret
3. 设置授权回调域名
4. 配置网页授权域名

## API 接口说明

### 1. 获取微信登录授权URL

```http
GET /api/v1/wechat/login-url
```

**响应示例：**

```json
{
  "code": 200,
  "msg": "获取微信登录URL成功",
  "data": {
    "login_url": "https://open.weixin.qq.com/connect/oauth2/authorize?..."
  }
}
```

### 2. 微信登录

```http
POST /api/v1/wechat/login
Content-Type: application/json

{
  "code": "微信授权码",
  "state": "状态参数（可选）"
}
```

**响应示例：**

```json
{
  "success": true,
  "token": "jwt_token_here",
  "user_info": {
    "user": {
      "user_id": "user_123",
      "username": "微信用户",
      "email": null,
      "avatar": null
    },
    "roles": ["user"],
    "permissions": []
  },
  "wechat_info": {
    "openid": "wx_openid_123",
    "nickname": "微信用户",
    "headimgurl": "https://example.com/avatar.jpg"
  },
  "message": "登录成功",
  "need_bind": false
}
```

### 3. 绑定微信账号

```http
POST /api/v1/wechat/bind
Content-Type: application/json

{
  "openid": "微信openid",
  "username": "现有用户名",
  "password": "密码"
}
```

### 4. 创建二维码登录

```http
POST /api/v1/wechat/qr/create
Content-Type: application/json

{
  "scene_str": "登录会话标识"
}
```

**响应示例：**

```json
{
  "ticket": "qr_ticket_123",
  "qr_code_url": "https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket=...",
  "scene_str": "login_session_123"
}
```

### 5. 检查二维码状态

```http
GET /api/v1/wechat/qr/status/{scene_str}
```

**响应示例：**

```json
{
  "status": "confirmed",
  "user_info": {
    "openid": "wx_openid_123",
    "nickname": "微信用户"
  },
  "message": "状态: confirmed"
}
```

### 6. 微信授权回调

```http
GET /api/v1/wechat/callback?code=授权码&state=状态参数
```

## 前端集成示例

### 1. 微信网页登录

```javascript
// 获取微信登录URL
async function getWechatLoginUrl() {
  const response = await fetch('/api/v1/wechat/login-url');
  const data = await response.json();
  
  if (data.code === 200) {
    // 跳转到微信授权页面
    window.location.href = data.data.login_url;
  }
}

// 处理微信回调
function handleWechatCallback() {
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  
  if (token) {
    // 保存token并跳转到主页
    localStorage.setItem('token', token);
    window.location.href = '/dashboard';
  }
}
```

### 2. 微信扫码登录

```javascript
// 创建二维码登录
async function createQRLogin() {
  const sceneStr = 'login_' + Date.now();
  const response = await fetch('/api/v1/wechat/qr/create', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ scene_str: sceneStr })
  });
  
  const data = await response.json();
  
  if (data.ticket) {
    // 显示二维码
    document.getElementById('qr-code').src = data.qr_code_url;
    
    // 开始轮询状态
    pollQRStatus(sceneStr);
  }
}

// 轮询二维码状态
function pollQRStatus(sceneStr) {
  const interval = setInterval(async () => {
    const response = await fetch(`/api/v1/wechat/qr/status/${sceneStr}`);
    const data = await response.json();
    
    if (data.status === 'confirmed') {
      clearInterval(interval);
      // 登录成功，保存token
      localStorage.setItem('token', data.token);
      window.location.href = '/dashboard';
    } else if (data.status === 'expired') {
      clearInterval(interval);
      alert('二维码已过期，请重新生成');
    }
  }, 2000); // 每2秒检查一次
}
```

### 3. 微信账号绑定

```javascript
// 绑定微信账号
async function bindWechatAccount(openid, username, password) {
  const response = await fetch('/api/v1/wechat/bind', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      openid: openid,
      username: username,
      password: password
    })
  });
  
  const data = await response.json();
  
  if (data.success) {
    // 绑定成功，保存token
    localStorage.setItem('token', data.token);
    window.location.href = '/dashboard';
  } else {
    alert(data.message);
  }
}
```

## 数据库设计

### 用户表扩展

需要在现有用户表中添加以下字段：

```sql
ALTER TABLE users ADD COLUMN wechat_openid VARCHAR(64) NULL;
ALTER TABLE users ADD COLUMN login_type VARCHAR(20) DEFAULT 'password';
```

### 微信用户关联表（可选）

```sql
CREATE TABLE wechat_users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id VARCHAR(64) NOT NULL,
  openid VARCHAR(64) NOT NULL UNIQUE,
  nickname VARCHAR(100),
  avatar_url VARCHAR(500),
  bind_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user_id (user_id),
  INDEX idx_openid (openid)
);
```

## 部署注意事项

1. **HTTPS要求**：微信开放平台要求回调地址必须使用HTTPS
2. **域名配置**：确保在微信开放平台正确配置授权域名
3. **Redis配置**：确保Redis服务正常运行，用于存储登录状态
4. **环境变量**：生产环境中使用环境变量管理敏感配置

## 安全考虑

1. **Token安全**：JWT token包含敏感信息，确保传输和存储安全
2. **状态验证**：验证微信回调的state参数防止CSRF攻击
3. **用户绑定**：限制一个微信账号只能绑定一个用户账号
4. **会话管理**：合理设置token过期时间和刷新机制

## 故障排除

### 常见问题

1. **获取不到用户信息**
    - 检查scope是否设置为snsapi_userinfo
    - 确认用户已关注公众号（服务号）

2. **回调地址错误**
    - 检查WECHAT_REDIRECT_URI配置
    - 确认域名在微信开放平台已配置

3. **二维码过期**
    - 检查Redis连接是否正常
    - 确认二维码过期时间配置

### 调试方法

1. 查看应用日志
2. 检查Redis中的状态数据
3. 使用微信开发者工具测试
4. 验证网络连接和DNS解析

## 扩展功能

可以考虑添加以下扩展功能：

1. **微信小程序登录**：支持小程序端登录
2. **微信支付集成**：结合支付功能
3. **消息推送**：微信模板消息推送
4. **用户画像**：基于微信数据的用户分析
