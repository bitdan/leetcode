#!/bin/bash

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "Please run this script as root"
        exit 1
    fi
}

# Check OS type
check_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    elif [ -f /etc/redhat-release ]; then
        OS="rhel"
    else
        echo "Unable to detect OS type"
        exit 1
    fi

    # If OpenCloudOS, treat as RHEL-based
    if [[ "$OS" == "opencloudos" ]]; then
        echo "Detected OpenCloudOS, treating as RHEL-based system"
        OS="rhel"
    fi
}

# Install Docker for CentOS/RHEL/OpenCloudOS
install_docker_redhat() {
    echo "Detected ${OS} system, installing Docker..."
    # Install required packages
    yum install -y yum-utils device-mapper-persistent-data lvm2
    # Add Docker repository
    yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    # Install Docker
    yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
}

# Install Docker for Debian/Ubuntu
install_docker_debian() {
    echo "Detected ${OS} system, installing Docker..."
    # Update package index and install dependencies
    apt update
    apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg
    # Add Docker's official GPG key and repository
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    # Install Docker
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
}

# Install Docker for OpenSUSE
install_docker_suse() {
    echo "Detected OpenSUSE system, installing Docker..."
    # Add Docker repository
    zypper addrepo https://download.docker.com/linux/opensuse/docker-ce.repo
    # Refresh repositories
    zypper refresh
    # Install Docker
    zypper install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
}

# Install Docker for Fedora
install_docker_fedora() {
    echo "Detected Fedora system, installing Docker..."
    # Add Docker repository
    dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
    # Install Docker
    dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
}

# Configure Docker settings
configure_docker() {
    echo "Configuring Docker settings..."
    # Create Docker configuration directory
    mkdir -p /etc/docker

    # Configure Docker daemon
    cat > /etc/docker/daemon.json <<EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "20m",
        "max-file": "3"
    },
    "storage-driver": "overlay2",
    "exec-opts": ["native.cgroupdriver=systemd"]
}
EOF

    # Create systemd directory
    mkdir -p /etc/systemd/system/docker.service.d

    # Restart Docker service
    systemctl daemon-reload
    systemctl restart docker
    systemctl enable docker

    # Verify installation
    if docker info >/dev/null 2>&1; then
        echo "Docker installed successfully!"
        docker --version
    else
        echo "Docker installation may have issues, please check system logs"
        exit 1
    fi
}

# Uninstall Docker function
uninstall_docker() {
    echo "Starting Docker uninstallation..."

    # Stop all running containers
    if command -v docker &> /dev/null; then
        echo "Stopping all running containers..."
        docker stop $(docker ps -aq) 2>/dev/null || true
    fi

    # Uninstall based on OS type
    case "$OS" in
        centos|rhel)
            echo "Removing Docker packages..."
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
            echo "Removing Docker packages..."
            apt remove --purge -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            apt remove --purge -y docker docker-engine docker.io containerd runc
            apt autoremove -y
            ;;
        opensuse*|sles)
            echo "Removing Docker packages..."
            zypper remove -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            zypper remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine
            ;;
        fedora)
            echo "Removing Docker packages..."
            dnf remove -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            dnf remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine
            ;;
    esac

    # Clean up Docker files and directories
    echo "Cleaning up Docker data and configuration files..."
    rm -rf /var/lib/docker
    rm -rf /var/lib/containerd
    rm -rf /etc/docker
    rm -rf /etc/systemd/system/docker.service.d
    rm -f /etc/apt/keyrings/docker.gpg 2>/dev/null
    rm -f /etc/apt/sources.list.d/docker.list 2>/dev/null

    echo "Docker uninstallation complete!"
}

# Show menu
show_menu() {
    echo "=== Docker Management Tool ==="
    echo "1. Install Docker"
    echo "2. Uninstall Docker"
    echo "3. Exit"
    echo "Please select an option (1-3): "
}

# Remove old Docker versions
remove_old_docker() {
    echo "Checking and removing old Docker versions..."
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

# Main Docker installation function
install_docker() {
    check_root
    check_os

    echo "Starting Docker installation..."

    # Check if Docker is already installed
    if command -v docker &> /dev/null; then
        echo "Docker is already installed"
        docker --version
        read -p "Do you want to remove existing version and reinstall? (y/n) " confirm
        if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
            # Stop all running containers
            echo "Stopping all running containers..."
            docker stop $(docker ps -aq) 2>/dev/null || true

            # Remove old version
            remove_old_docker
        else
            echo "Keeping existing Docker version, installation cancelled"
            return
        fi
    else
        # Check and remove any old packages
        remove_old_docker
    fi

    # Install based on OS type
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
            echo "Unsupported operating system: $OS"
            exit 1
            ;;
    esac

    # Configure Docker
    configure_docker
    echo "Docker installation and configuration complete!"
}

# Main program loop
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
                echo "Warning: This will remove all Docker containers, images, and configurations."
                read -p "Are you sure you want to continue? (y/n) " confirm
                if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
                    uninstall_docker
                else
                    echo "Uninstallation cancelled"
                fi
                ;;
            3)
                echo "Exiting program"
                exit 0
                ;;
            *)
                echo "Invalid choice, please try again"
                ;;
        esac
        echo
    done
}

# Execute main program
main
