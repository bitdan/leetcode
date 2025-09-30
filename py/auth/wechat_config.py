"""
微信登录配置文件
"""
import os
from typing import Optional
from config.config import (
    WECHAT_APP_ID, 
    WECHAT_APP_SECRET, 
    WECHAT_REDIRECT_URI, 
    FRONTEND_DOMAIN,
    QR_EXPIRE_TIME,
    QR_SIZE
)


class WechatConfig:
    """微信配置类"""
    
    def __init__(self):
        # 微信开放平台配置
        self.app_id: str = WECHAT_APP_ID
        self.app_secret: str = WECHAT_APP_SECRET
        
        # 回调地址配置
        self.redirect_uri: str = WECHAT_REDIRECT_URI
        self.frontend_domain: str = FRONTEND_DOMAIN
        
        # 微信API配置
        self.wx_api_base: str = "https://api.weixin.qq.com"
        self.wx_qr_api_base: str = "https://api.weixin.qq.com/cgi-bin"
        
        # 二维码配置
        self.qr_expire_time: int = QR_EXPIRE_TIME
        self.qr_size: int = QR_SIZE
        
        # 验证配置
        self.validate_config()
    
    def validate_config(self):
        """验证配置"""
        if self.app_id == "your_wechat_app_id":
            print("警告: 请设置正确的微信AppID")
        if self.app_secret == "your_wechat_app_secret":
            print("警告: 请设置正确的微信AppSecret")
    
    def get_wechat_login_url(self) -> str:
        """获取微信登录授权URL"""
        import uuid
        state = str(uuid.uuid4())
        params = {
            "appid": self.app_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "snsapi_userinfo",
            "state": state
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://open.weixin.qq.com/connect/oauth2/authorize?{query_string}#wechat_redirect"
    
    def get_success_redirect_url(self, token: str) -> str:
        """获取登录成功重定向URL"""
        return f"{self.frontend_domain}/login/success?token={token}"
    
    def get_bind_redirect_url(self, openid: str) -> str:
        """获取绑定页面重定向URL"""
        return f"{self.frontend_domain}/login/bind?openid={openid}"
    
    def get_failed_redirect_url(self, message: str) -> str:
        """获取登录失败重定向URL"""
        return f"{self.frontend_domain}/login/failed?message={message}"


# 全局微信配置实例
wechat_config = WechatConfig()
