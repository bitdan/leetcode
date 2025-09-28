#!/usr/bin/env python3
"""
生成密码哈希的脚本
"""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 生成admin123的哈希
password = "admin123"
password_hash = pwd_context.hash(password)

print(f"密码: {password}")
print(f"哈希: {password_hash}")

# 验证哈希
is_valid = pwd_context.verify(password, password_hash)
print(f"验证结果: {is_valid}")
