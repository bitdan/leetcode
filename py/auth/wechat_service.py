import uuid
import logging
import hashlib
import time
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from auth.models import WechatUserInfo, WechatLoginResponse, QRCodeLoginResponse, QRCodeStatusResponse, User
from auth.user_service import user_service
from auth.redis_client import redis_client
from auth.wechat_config import wechat_config
from auth.jwt_handler import jwt_handler

logger = logging.getLogger(__name__)


class WechatService:
    def __init__(self):
        # 使用配置文件中的微信配置
        self.app_id = wechat_config.app_id
        self.app_secret = wechat_config.app_secret
        self.redirect_uri = wechat_config.redirect_uri
        
        # 微信API地址
        self.wx_api_base = wechat_config.wx_api_base
        self.wx_qr_api_base = wechat_config.wx_qr_api_base
        
        # 模拟微信用户数据库 - 实际项目中应该使用真实数据库
        self.wechat_users_db: Dict[str, Dict[str, Any]] = {}

    def _make_wx_request(self, url: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """发起微信API请求"""
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"微信API请求失败: {e}")
            return None

    def get_access_token(self, code: str) -> Optional[str]:
        """通过code获取access_token"""
        url = f"{self.wx_api_base}/sns/oauth2/access_token"
        params = {
            "appid": self.app_id,
            "secret": self.app_secret,
            "code": code,
            "grant_type": "authorization_code"
        }
        
        result = self._make_wx_request(url, params)
        if result and "access_token" in result:
            return result["access_token"]
        return None

    def get_user_info(self, access_token: str, openid: str) -> Optional[WechatUserInfo]:
        """获取微信用户信息"""
        url = f"{self.wx_api_base}/sns/userinfo"
        params = {
            "access_token": access_token,
            "openid": openid,
            "lang": "zh_CN"
        }
        
        result = self._make_wx_request(url, params)
        if result and "openid" in result:
            return WechatUserInfo(
                openid=result["openid"],
                nickname=result.get("nickname"),
                sex=result.get("sex"),
                province=result.get("province"),
                city=result.get("city"),
                country=result.get("country"),
                headimgurl=result.get("headimgurl"),
                unionid=result.get("unionid")
            )
        return None

    def create_qr_code_ticket(self, scene_str: str) -> Optional[str]:
        """创建二维码ticket（模拟实现）"""
        try:
            # 实际实现中应该调用微信接口创建ticket
            # 这里为了演示，我们生成一个模拟的ticket
            ticket = f"qr_ticket_{scene_str}_{int(time.time())}"
            
            # 将ticket存储到Redis，设置过期时间
            redis_client.redis_client.setex(
                f"wechat_qr:{ticket}", 
                wechat_config.qr_expire_time,
                scene_str
            )
            
            return ticket
        except Exception as e:
            logger.error(f"创建二维码ticket失败: {e}")
            return None

    def get_qr_code_url(self, ticket: str) -> str:
        """获取二维码URL"""
        # 实际实现中应该调用微信接口获取二维码URL
        # 这里返回一个模拟的URL
        return f"https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket={ticket}"

    def create_qr_code_login(self, scene_str: str) -> Optional[QRCodeLoginResponse]:
        """创建二维码登录"""
        try:
            ticket = self.create_qr_code_ticket(scene_str)
            if not ticket:
                return None
            
            qr_code_url = self.get_qr_code_url(ticket)
            
            # 在Redis中存储二维码登录状态
            qr_status = {
                "status": "waiting",  # waiting, scanned, confirmed, expired
                "scene_str": scene_str,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(minutes=5)).isoformat()
            }
            redis_client.redis_client.setex(
                f"wechat_qr_status:{scene_str}",
                wechat_config.qr_expire_time,
                str(qr_status)
            )
            
            return QRCodeLoginResponse(
                ticket=ticket,
                qr_code_url=qr_code_url,
                scene_str=scene_str
            )
        except Exception as e:
            logger.error(f"创建二维码登录失败: {e}")
            return None

    def check_qr_code_status(self, scene_str: str) -> QRCodeStatusResponse:
        """检查二维码登录状态"""
        try:
            status_data = redis_client.redis_client.get(f"wechat_qr_status:{scene_str}")
            if not status_data:
                return QRCodeStatusResponse(
                    status="expired",
                    message="二维码已过期"
                )
            
            # 这里简化处理，实际应该从微信服务器获取状态
            # 模拟不同的状态变化
            import random
            statuses = ["waiting", "scanned", "confirmed"]
            current_status = random.choice(statuses)
            
            wechat_info = None
            if current_status == "confirmed":
                # 模拟获取到的微信用户信息
                wechat_info = WechatUserInfo(
                    openid=f"mock_openid_{scene_str}",
                    nickname="微信用户",
                    headimgurl="https://example.com/avatar.jpg"
                )
            
            return QRCodeStatusResponse(
                status=current_status,
                user_info=wechat_info,
                message=f"状态: {current_status}"
            )
        except Exception as e:
            logger.error(f"检查二维码状态失败: {e}")
            return QRCodeStatusResponse(
                status="error",
                message="检查状态失败"
            )

    def wechat_login(self, code: str) -> WechatLoginResponse:
        """微信登录"""
        try:
            # 1. 获取access_token
            access_token = self.get_access_token(code)
            if not access_token:
                return WechatLoginResponse(
                    success=False,
                    message="获取微信授权失败"
                )
            
            # 2. 获取用户openid（简化处理，实际需要调用微信API）
            openid = f"wx_openid_{hashlib.md5(code.encode()).hexdigest()[:16]}"
            
            # 3. 检查是否已绑定用户
            user_dict = self.wechat_users_db.get(openid)
            if user_dict:
                # 已绑定，直接登录
                user = user_service.get_user_by_id(user_dict["user_id"])
                if user:
                    token = user_service.create_user_session(user)
                    user_info = user_service.get_user_info(user.user_id)
                    
                    return WechatLoginResponse(
                        success=True,
                        token=token,
                        user_info=user_info,
                        wechat_info=WechatUserInfo(
                            openid=openid,
                            nickname=user_dict.get("nickname", "微信用户")
                        ),
                        message="登录成功"
                    )
            
            # 4. 未绑定，返回需要绑定的信息
            return WechatLoginResponse(
                success=False,
                need_bind=True,
                wechat_info=WechatUserInfo(
                    openid=openid,
                    nickname="微信用户"
                ),
                message="请绑定现有账号"
            )
            
        except Exception as e:
            logger.error(f"微信登录失败: {e}")
            return WechatLoginResponse(
                success=False,
                message=f"登录失败: {str(e)}"
            )

    def bind_wechat_user(self, openid: str, username: str, password: str) -> WechatLoginResponse:
        """绑定微信用户"""
        try:
            # 1. 验证用户名和密码（直接验证，不通过authenticate_user）
            user_dict = user_service.users_db.get(username)
            if not user_dict:
                return WechatLoginResponse(
                    success=False,
                    message="用户名或密码错误"
                )
            
            # 验证密码
            if not jwt_handler.verify_password(password, user_dict["password_hash"]):
                return WechatLoginResponse(
                    success=False,
                    message="用户名或密码错误"
                )
            
            # 构建User对象
            user = User(
                user_id=user_dict["user_id"],
                username=user_dict["username"],
                email=user_dict["email"],
                avatar=user_dict["avatar"],
                created_at=datetime.fromisoformat(user_dict["created_at"]),
                updated_at=datetime.fromisoformat(user_dict["updated_at"])
            )
            
            # 2. 检查用户是否已绑定其他微信账号
            for wx_openid, wx_user in self.wechat_users_db.items():
                if wx_user["user_id"] == user.user_id and wx_openid != openid:
                    return WechatLoginResponse(
                        success=False,
                        message="该账号已绑定其他微信"
                    )
            
            # 3. 绑定微信账号
            self.wechat_users_db[openid] = {
                "user_id": user.user_id,
                "openid": openid,
                "username": user.username,
                "nickname": f"微信用户_{user.username}",
                "bind_time": datetime.now().isoformat()
            }
            
            # 4. 创建登录会话
            token = user_service.create_user_session(user)
            user_info = user_service.get_user_info(user.user_id)
            
            return WechatLoginResponse(
                success=True,
                token=token,
                user_info=user_info,
                wechat_info=WechatUserInfo(
                    openid=openid,
                    nickname=self.wechat_users_db[openid]["nickname"]
                ),
                message="绑定成功"
            )
            
        except Exception as e:
            logger.error(f"绑定微信用户失败: {e}")
            return WechatLoginResponse(
                success=False,
                message=f"绑定失败: {str(e)}"
            )

    def qr_code_login(self, scene_str: str, wechat_info: WechatUserInfo) -> WechatLoginResponse:
        """二维码登录"""
        try:
            # 1. 检查是否已绑定用户
            user_dict = self.wechat_users_db.get(wechat_info.openid)
            if user_dict:
                # 已绑定，直接登录
                user = user_service.get_user_by_id(user_dict["user_id"])
                if user:
                    token = user_service.create_user_session(user)
                    user_info = user_service.get_user_info(user.user_id)
                    
                    # 更新二维码状态为已确认
                    qr_status = {
                        "status": "confirmed",
                        "scene_str": scene_str,
                        "user_info": wechat_info.dict(),
                        "confirmed_at": datetime.now().isoformat()
                    }
                    redis_client.redis_client.setex(
                        f"wechat_qr_status:{scene_str}",
                        wechat_config.qr_expire_time,
                        str(qr_status)
                    )
                    
                    return WechatLoginResponse(
                        success=True,
                        token=token,
                        user_info=user_info,
                        wechat_info=wechat_info,
                        message="登录成功"
                    )
            
            # 2. 未绑定，返回需要绑定的信息
            return WechatLoginResponse(
                success=False,
                need_bind=True,
                wechat_info=wechat_info,
                message="请先绑定微信账号"
            )
            
        except Exception as e:
            logger.error(f"二维码登录失败: {e}")
            return WechatLoginResponse(
                success=False,
                message=f"登录失败: {str(e)}"
            )

    def get_wechat_login_url(self) -> str:
        """获取微信登录授权URL"""
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


# 全局微信服务实例
wechat_service = WechatService()
