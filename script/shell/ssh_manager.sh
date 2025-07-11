#!/bin/bash

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then
    echo "请使用 root 权限运行此脚本"
    exit 1
fi

# 备份原配置文件
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
echo "已备份原配置文件到 /etc/ssh/sshd_config.backup"

# 定义配置文件路径
SSHD_CONFIG="/etc/ssh/sshd_config"

# 函数：智能更新配置
update_config() {
    local key=$1
    local value=$2

    # 检查是否已经存在非注释的配置
    if grep -q "^${key}\s" "$SSHD_CONFIG"; then
        # 如果存在，直接更新该行
        sed -i "s/^${key}.*/${key} ${value}/" "$SSHD_CONFIG"
        echo "更新配置: ${key} ${value}"
    else
        # 检查是否存在注释的配置
        if grep -q "^#${key}\s" "$SSHD_CONFIG"; then
            # 如果存在注释的配置，取消注释并更新
            sed -i "s/^#${key}.*/${key} ${value}/" "$SSHD_CONFIG"
            echo "启用配置: ${key} ${value}"
        else
            # 如果不存在，添加新配置到文件末尾
            echo "${key} ${value}" >> "$SSHD_CONFIG"
            echo "添加配置: ${key} ${value}"
        fi
    fi
}

# 更新SSH配置
update_config "Port" "822"
update_config "RSAAuthentication" "yes"
update_config "PubkeyAuthentication" "yes"
update_config "PasswordAuthentication" "no"

echo "配置更新完成"

# 检查配置文件语法
echo "检查配置文件语法..."
sshd -t
if [ $? -ne 0 ]; then
    echo "配置文件存在语法错误，正在恢复备份..."
    cp /etc/ssh/sshd_config.backup /etc/ssh/sshd_config
    echo "已恢复原配置"
    exit 1
fi

# 重启 SSH 服务
echo "正在重启 SSH 服务..."
if command -v systemctl &> /dev/null; then
    systemctl restart sshd
else
    service sshd restart
fi

echo "
========================================
SSH 配置已完成！请注意以下变更：
1. SSH 端口已改为: 822
2. 已启用密钥认证
3. 已禁用密码登录

在断开当前连接之前，请新开一个终端测试能否通过新端口连接：
ssh -p 822 user@your-server-ip

如果无法连接，请检查：
1. 是否已正确配置防火墙规则
2. 云服务器安全组是否已开放 822 端口
3. SSH 密钥是否已正确配置
========================================"
