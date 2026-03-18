#!/usr/bin/env python3
"""
生成密码哈希的脚本
"""
import bcrypt


def normalize_password(password: str) -> bytes:
    encoded = password.encode("utf-8")
    return encoded[:72] if len(encoded) > 72 else encoded

# 生成admin123的哈希
password = "admin123"
password_hash = bcrypt.hashpw(normalize_password(password), bcrypt.gensalt()).decode("utf-8")

print(f"密码: {password}")
print(f"哈希: {password_hash}")

# 验证哈希
is_valid = bcrypt.checkpw(normalize_password(password), password_hash.encode("utf-8"))
print(f"验证结果: {is_valid}")
