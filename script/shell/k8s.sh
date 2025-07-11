#!/bin/bash

# 定义主机IP映射
declare -A HOST_IPS=(
    ["master"]="43.156.83.246"
    ["node1"]="43.134.80.61"
)

# 显示机器选择菜单
echo "请选择当前机器的角色："
echo "1. Master"
echo "2. Node1"
echo "4. 退出"

# 读取用户选择
read -p "请输入选择（1/2/4）: " choice

# 根据选择设置主机名和IP
case $choice in
    1)
        HOSTNAME="master"
        ;;
    2)
        HOSTNAME="node1"
        ;;
    4)
        echo "退出脚本"
        exit 0
        ;;
    *)
        echo "无效选择，请重新运行脚本并选择有效选项！"
        exit 1
        ;;
esac

# 关闭 SELinux
echo "关闭 SELinux"
setenforce 0
sed -i --follow-symlinks 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/sysconfig/selinux

# 配置网桥的 IPv4 流量
echo "配置网桥的 IPv4 流量"
cat > /etc/sysctl.d/k8s.conf << EOF
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1

EOF

echo "net.ipv4.ip_forward = 1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p


# 应用 sysctl 设置
sysctl --system

# 网卡信息配置
PARENT_INTERFACE="eth0"
VIRTUAL_INTERFACE="${PARENT_INTERFACE}:1"
NEW_IP="${HOST_IPS[$HOSTNAME]}"
NETMASK="255.255.255.0"

# 创建网卡配置文件
cat > /etc/sysconfig/network-scripts/ifcfg-${VIRTUAL_INTERFACE} << EOF
DEVICE=${VIRTUAL_INTERFACE}
TYPE=Ethernet
BOOTPROTO=static
ONBOOT=yes
IPADDR=${NEW_IP}
NETMASK=${NETMASK}
EOF

# 重启网络服务
systemctl restart network

# 验证配置
ip addr | grep ${NEW_IP}

# 添加 Kubernetes 官方仓库
cat <<EOF > kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://mirrors.aliyun.com/kubernetes/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=0
repo_gpgcheck=0
gpgkey=https://mirrors.aliyun.com/kubernetes/yum/doc/yum-key.gpg https://mirrors.aliyun.com/kubernetes/yum/doc/rpm-package-key.gpg
EOF

mv kubernetes.repo /etc/yum.repos.d/

# 安装 kubernetes 组件
yum install -y kubelet-1.23.0-0 kubectl-1.23.0-0 kubeadm-1.23.0-0

systemctl enable kubelet
systemctl start kubelet
echo "kubelet install ok"

