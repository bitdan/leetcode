#!/bin/bash

# 检查是否以 root 权限运行
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "请以 root 权限运行此脚本"
        exit 1
    fi
}

# 检查操作系统类型
check_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    elif [ -f /etc/redhat-release ]; then
        OS="rhel"
    else
        echo "无法检测操作系统类型"
        exit 1
    fi

    # 如果是 OpenCloudOS，设置为基于 RHEL 的系统
    if [[ "$OS" == "opencloudos" ]]; then
        echo "检测到 OpenCloudOS 系统，作为 RHEL 系列处理"
        OS="rhel"
    fi
}

# 安装 Docker 的函数定义 - CentOS/RHEL/OpenCloudOS
install_docker_redhat() {
    echo "检测到 ${OS} 系统，开始安装 Docker..."
    # 安装必要的工具
    yum install -y yum-utils device-mapper-persistent-data lvm2
    # 添加 Docker 仓库
    yum-config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
    # 安装 Docker
    yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
}

# 安装 Docker 的函数定义 - Debian/Ubuntu
install_docker_debian() {
    echo "检测到 ${OS} 系统，开始安装 Docker..."
    # 更新包索引并安装依赖
    apt update
    apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg
    # 添加 Docker GPG 密钥和仓库
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/$(. /etc/os-release; echo "$ID")/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/$(. /etc/os-release; echo "$ID") $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    # 安装 Docker
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
}

# 安装 Docker 的函数定义 - OpenSUSE
install_docker_suse() {
    echo "检测到 OpenSUSE 系统，开始安装 Docker..."
    # 添加 Docker 仓库
    zypper addrepo https://mirrors.aliyun.com/docker-ce/linux/opensuse/docker-ce.repo
    # 刷新软件源
    zypper refresh
    # 安装 Docker
    zypper install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
}

# 安装 Docker 的函数定义 - Fedora
install_docker_fedora() {
    echo "检测到 Fedora 系统，开始安装 Docker..."
    # 添加 Docker 仓库
    dnf config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/fedora/docker-ce.repo
    # 安装 Docker
    dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
}

# 配置 Docker 通用设置
configure_docker() {
    echo "配置 Docker 设置..."
    # 创建 Docker 配置目录
    mkdir -p /etc/docker

    # 配置 Docker 守护进程
    cat > /etc/docker/daemon.json <<EOF
{
    "registry-mirrors": [
        "https://docker.1panel.live"
    ],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "20m",
        "max-file": "3"
    },
    "storage-driver": "overlay2",
    "exec-opts": ["native.cgroupdriver=systemd"]
}
EOF

    # 创建 systemd 目录
    mkdir -p /etc/systemd/system/docker.service.d

    # 重启 Docker 服务
    systemctl daemon-reload
    systemctl restart docker
    systemctl enable docker

    # 验证安装
    if docker info >/dev/null 2>&1; then
        echo "Docker 安装成功！"
        docker --version
    else
        echo "Docker 安装可能出现问题，请检查系统日志"
        exit 1
    fi
}

# 卸载 Docker 的函数
uninstall_docker() {
    echo "开始卸载 Docker..."

    # 停止所有运行的容器
    if command -v docker &> /dev/null; then
        echo "停止所有运行中的容器..."
        docker stop $(docker ps -aq) 2>/dev/null || true
    fi

    # 根据操作系统类型执行卸载
    case "$OS" in
        centos|rhel)
            echo "卸载 Docker 包..."
            yum remove -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            yum remove -y docker \
                        docker-client \
                        docker-client-latest \
                        docker-common \
                        docker-latest \
                        docker-latest-logrotate \
                        docker-logrotate \
                        docker-engine
            ;;
        debian|ubuntu)
            echo "卸载 Docker 包..."
            apt remove --purge -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            apt remove --purge -y docker docker-engine docker.io containerd runc
            apt autoremove -y
            ;;
        opensuse*|sles)
            echo "卸载 Docker 包..."
            zypper remove -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            zypper remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine
            ;;
        fedora)
            echo "卸载 Docker 包..."
            dnf remove -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            dnf remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine
            ;;
    esac

    # 清理 Docker 相关文件和目录
    echo "清理 Docker 数据和配置文件..."
    rm -rf /var/lib/docker
    rm -rf /var/lib/containerd
    rm -rf /etc/docker
    rm -rf /etc/systemd/system/docker.service.d
    rm -f /etc/apt/keyrings/docker.gpg 2>/dev/null
    rm -f /etc/apt/sources.list.d/docker.list 2>/dev/null

    echo "Docker 卸载完成！"
}

# 显示菜单
show_menu() {
    echo "=== Docker 管理工具 ==="
    echo "1. 安装 Docker"
    echo "2. 卸载 Docker"
    echo "3. 退出"
    echo "请选择操作 (1-3): "
}



# 删除旧版本 Docker 的函数
remove_old_docker() {
    echo "检查并删除旧版本 Docker..."
    case "$OS" in
        centos|rhel)
            yum remove -y docker \
                      docker-client \
                      docker-client-latest \
                      docker-common \
                      docker-latest \
                      docker-latest-logrotate \
                      docker-logrotate \
                      docker-engine
            ;;
        debian|ubuntu)
            apt remove -y docker docker-engine docker.io containerd runc
            ;;
        opensuse*|sles)
            zypper remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine
            ;;
        fedora)
            dnf remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine
            ;;
    esac
}

# 安装 Docker 主函数
install_docker() {
    check_root
    check_os

    echo "开始安装 Docker..."

    # 检查是否已安装 Docker
    if command -v docker &> /dev/null; then
        echo "检测到系统已安装 Docker"
        docker --version
        read -p "是否要删除现有版本并重新安装？(y/n) " confirm
        if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
            # 停止所有运行中的容器
            echo "停止所有运行中的容器..."
            docker stop $(docker ps -aq) 2>/dev/null || true

            # 删除旧版本
            remove_old_docker
        else
            echo "保留现有 Docker 版本，安装操作已取消"
            return
        fi
    else
        # 检查并删除可能存在的旧版本包
        remove_old_docker
    fi

    # 根据操作系统执行相应的安装过程
    case "$OS" in
        centos|rhel)
            install_docker_redhat
            ;;
        debian|ubuntu)
            install_docker_debian
            ;;
        opensuse*|sles)
            install_docker_suse
            ;;
        fedora)
            install_docker_fedora
            ;;
        *)
            echo "不支持的操作系统：$OS"
            exit 1
            ;;
    esac

    # 配置 Docker
    configure_docker
    echo "Docker 安装和配置完成！"
}


# 主程序循环
main() {
    check_root
    check_os

    while true; do
        show_menu
        read choice
        case $choice in
            1)
                install_docker
                ;;
            2)
                echo "警告：这将删除所有 Docker 容器和镜像，以及相关配置。"
                read -p "确定要继续吗？(y/n) " confirm
                if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
                    uninstall_docker
                else
                    echo "取消卸载操作"
                fi
                ;;
            3)
                echo "退出程序"
                exit 0
                ;;
            *)
                echo "无效的选择，请重试"
                ;;
        esac
        echo
    done
}

# 执行主程序
main
