# 微信登录配置设置说明

## 环境变量配置

在项目的 `.env` 文件中添加以下微信登录相关的环境变量：

```bash
# 微信登录配置
WECHAT_APP_ID=your_wechat_app_id_here
WECHAT_APP_SECRET=your_wechat_app_secret_here
WECHAT_REDIRECT_URI=http://your-domain.com/api/v1/wechat/callback
FRONTEND_DOMAIN=http://your-frontend-domain.com

# 二维码配置（可选）
QR_EXPIRE_TIME=300
QR_SIZE=300
```

## 配置说明

### 必需配置

1. **WECHAT_APP_ID**: 微信开放平台的AppID
    - 在微信开放平台注册应用后获得
    - 示例：`wx1234567890abcdef`

2. **WECHAT_APP_SECRET**: 微信开放平台的AppSecret
    - 与AppID配对使用
    - 示例：`abcdef1234567890abcdef1234567890`

3. **WECHAT_REDIRECT_URI**: 微信授权回调地址
    - 必须是HTTPS地址（生产环境）
    - 需要在微信开放平台配置授权回调域名
    - 示例：`https://your-domain.com/api/v1/wechat/callback`

4. **FRONTEND_DOMAIN**: 前端域名
    - 用于登录成功后的重定向
    - 示例：`https://your-frontend-domain.com`

### 可选配置

1. **QR_EXPIRE_TIME**: 二维码过期时间（秒）
    - 默认：300秒（5分钟）
    - 建议范围：120-600秒

2. **QR_SIZE**: 二维码大小（像素）
    - 默认：300px
    - 建议范围：200-500px

## 配置验证

启动应用时，系统会自动验证配置：

- 如果AppID或AppSecret未设置或使用默认值，会显示警告信息
- 确保回调地址格式正确且可访问
- 确保前端域名配置正确

## 微信开放平台配置

### 1. 注册微信开放平台账号

访问：https://open.weixin.qq.com/

### 2. 创建网站应用

- 填写应用基本信息
- 获取AppID和AppSecret
- 配置授权回调域名

### 3. 配置授权回调域名

- 域名必须是已备案的域名
- 必须使用HTTPS协议
- 示例：`your-domain.com`

### 4. 配置网页授权域名

- 与授权回调域名相同
- 用于获取用户基本信息

## 测试配置

运行测试脚本验证配置是否正确：

```bash
cd py
python run_wechat_test.py
```

## 常见问题

### 1. 获取不到用户信息

- 检查scope是否设置为snsapi_userinfo
- 确认用户已关注公众号（服务号）

### 2. 回调地址错误

- 检查WECHAT_REDIRECT_URI配置
- 确认域名在微信开放平台已配置
- 确保使用HTTPS协议

### 3. 二维码过期

- 检查Redis连接是否正常
- 确认二维码过期时间配置合理

### 4. 配置不生效

- 确认.env文件在正确位置
- 重启应用使配置生效
- 检查环境变量名称是否正确

## 安全注意事项

1. **保护AppSecret**:
    - 不要将AppSecret提交到代码仓库
    - 使用环境变量管理敏感信息

2. **HTTPS要求**:
    - 生产环境必须使用HTTPS
    - 微信开放平台要求回调地址使用HTTPS

3. **域名验证**:
    - 确保回调域名在微信开放平台已正确配置
    - 定期检查域名配置状态

4. **访问控制**:
    - 限制回调接口的访问权限
    - 实现适当的错误处理

## 部署建议

### 开发环境

```bash
WECHAT_APP_ID=your_dev_app_id
WECHAT_APP_SECRET=your_dev_app_secret
WECHAT_REDIRECT_URI=http://localhost:8000/api/v1/wechat/callback
FRONTEND_DOMAIN=http://localhost:3000
```

### 生产环境

```bash
WECHAT_APP_ID=your_prod_app_id
WECHAT_APP_SECRET=your_prod_app_secret
WECHAT_REDIRECT_URI=https://your-domain.com/api/v1/wechat/callback
FRONTEND_DOMAIN=https://your-frontend-domain.com
```

## 监控和维护

1. **定期检查**:
    - 微信API调用成功率
    - 登录成功率和错误率
    - Redis连接状态

2. **日志监控**:
    - 记录微信API调用日志
    - 监控异常登录行为
    - 跟踪用户绑定情况

3. **配置更新**:
    - 定期更新微信SDK版本
    - 关注微信API更新通知
    - 及时处理配置变更
