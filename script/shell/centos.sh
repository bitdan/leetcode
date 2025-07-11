#!/bin/bash

# 判断是否为海外服务器（通过检测外网 IP 判断）
if curl -s https://www.cloudflare.com/cdn-cgi/trace | grep -q "loc=CN"; then
    # 获取操作系统版本信息
    if grep -q "CentOS Linux 7" /etc/os-release; then
        # 备份旧的 yum 源配置文件
        cp /etc/yum.repos.d/CentOS-Base.repo /etc/yum.repos.d/CentOS-Base.repo.bak

        # 下载阿里云 CentOS 7 yum 源配置文件
        wget -O /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-7.repo

        echo "阿里云 CentOS 7 yum 源配置文件已下载"
    elif grep -q "CentOS Linux 8" /etc/os-release; then
        # 备份旧的 yum 源配置文件
        cp /etc/yum.repos.d/CentOS-Base.repo /etc/yum.repos.d/CentOS-Base.repo.bak

        # 下载阿里云 CentOS 8 yum 源配置文件
        wget -O /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-8.repo

        echo "阿里云 CentOS 8 yum 源配置文件已下载"
    elif grep -q "OpenCloudOS" /etc/os-release; then
        # 针对 OpenCloudOS，可以根据需要下载对应的源文件
        echo "当前系统为 OpenCloudOS，跳过阿里云源配置"
    else
        echo "未检测到支持的 CentOS 或 OpenCloudOS 系统，跳过源配置"
    fi
else
    echo "非中国大陆服务器，跳过阿里云源配置"
fi


# 安装 EPEL 源
sudo yum install -y epel-release

# 清理 yum 缓存并重建缓存
yum clean all
yum makecache

# 更新系统
sudo yum update -y

# 安装开发工具和其他常用软件
sudo yum groupinstall -y 'Development Tools'
sudo yum install -y openssl-devel htop telnet


echo "yum 配置完成！"
