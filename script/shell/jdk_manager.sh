#!/bin/bash

# 显示菜单
show_menu() {
    echo "=== JDK 管理工具 ==="
    echo "1. 安装 JDK"
    echo "2. 卸载 JDK"
    echo "3. 退出"
    echo "请选择操作 (1-3): "
}

# 安装 JDK 函数
install_jdk() {
    # 检查当前目录中的JDK压缩包
    jdk_files=($(ls jdk*.tar.gz 2>/dev/null))

    if [ ${#jdk_files[@]} -eq 0 ]; then
        echo "错误：当前目录中没有找到JDK压缩包"
        return 1
    fi

    # 列出可用的JDK压缩包
    echo "找到以下JDK压缩包："
    for i in "${!jdk_files[@]}"; do
        echo "$((i+1)). ${jdk_files[$i]}"
    done

    # 让用户选择要安装的JDK
    echo "请选择要安装的JDK（输入数字）："
    read choice

    if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt ${#jdk_files[@]} ]; then
        echo "无效的选择"
        return 1
    fi

    selected_jdk="${jdk_files[$((choice-1))]}"

    # 创建安装目录
    sudo mkdir -p /usr/local/java

    # 解压选中的JDK
    echo "正在解压 $selected_jdk ..."
    sudo tar -xzf "$selected_jdk" -C /usr/local/java

    # 获取解压后的目录名
    jdk_dir=$(tar -tzf "$selected_jdk" | head -1 | cut -f1 -d"/")

    # 检查是否已存在 JAVA_HOME 设置
    if grep -q "JAVA_HOME=/usr/local/java/$jdk_dir" /etc/profile; then
        echo "环境变量已存在，跳过添加"
    else
        # 设置环境变量
        echo "export JAVA_HOME=/usr/local/java/$jdk_dir" | sudo tee -a /etc/profile
        echo "export PATH=\$JAVA_HOME/bin:\$PATH" | sudo tee -a /etc/profile
    fi

    # 使环境变量生效
    source /etc/profile

    # 验证安装
    echo "验证 JDK 安装："
    java -version

    echo "JDK $selected_jdk 安装完成"
    echo "请重新登录或运行 'source /etc/profile' 以使环境变量生效"
}

# 卸载 JDK 函数
uninstall_jdk() {
    # 定义 JDK 安装目录
    jdk_install_dir="/usr/local/java"

    # 检查 JDK 安装目录是否存在
    if [ ! -d "$jdk_install_dir" ]; then
        echo "错误：JDK 安装目录 $jdk_install_dir 不存在"
        return 1
    fi

    # 列出安装的 JDK 版本
    jdk_dirs=($(ls -d $jdk_install_dir/* 2>/dev/null))

    if [ ${#jdk_dirs[@]} -eq 0 ]; then
        echo "错误：没有找到已安装的 JDK"
        return 1
    fi

    echo "找到以下已安装的 JDK 版本："
    for i in "${!jdk_dirs[@]}"; do
        echo "$((i+1)). ${jdk_dirs[$i]}"
    done

    # 让用户选择要卸载的 JDK
    echo "请选择要卸载的 JDK（输入数字）："
    read choice

    if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt ${#jdk_dirs[@]} ]; then
        echo "无效的选择"
        return 1
    fi

    selected_jdk="${jdk_dirs[$((choice-1))]}"

    # 确认卸载操作
    echo "您确定要卸载 JDK $selected_jdk 吗？(y/n)"
    read confirm

    if [[ "$confirm" != "y" ]]; then
        echo "取消卸载"
        return 0
    fi

    # 删除选中的 JDK 目录
    sudo rm -rf "$selected_jdk"

    # 从环境变量中移除 JAVA_HOME 和 PATH 设置
    sudo sed -i "\|$selected_jdk|d" /etc/profile

    echo "JDK $selected_jdk 卸载完成"
    echo "请重新登录或运行 'source /etc/profile' 以更新环境变量"
}

# 主程序循环
while true; do
    show_menu
    read choice
    case $choice in
        1)
            install_jdk
            ;;
        2)
            uninstall_jdk
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
