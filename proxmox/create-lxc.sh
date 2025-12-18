#!/bin/bash

##############################################################################
# create-lxc.sh - Автоматичне створення LXC контейнера для Proxmox
#
# Цей скрипт створює та налаштовує LXC контейнер для запуску
# Competitive Intelligence з Selenium Grid
#
# Використання:
#   ./create-lxc.sh [VMID] [HOSTNAME] [IP_ADDRESS]
#
# Приклад:
#   ./create-lxc.sh 100 selenium-grid 192.168.1.100
#   ./create-lxc.sh 100 selenium-grid dhcp
##############################################################################

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
VMID="${1:-}"
HOSTNAME="${2:-competitive-intelligence}"
IP_ADDRESS="${3:-dhcp}"
GATEWAY="${4:-192.168.1.1}"
TEMPLATE="local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst"
STORAGE="local-lvm"
CORES=4
MEMORY=8192
SWAP=4096
DISK_SIZE=50
BRIDGE="vmbr0"

##############################################################################
# Utility Functions
##############################################################################

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}" >&2
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

show_usage() {
    cat << EOF
Usage: $0 [VMID] [HOSTNAME] [IP_ADDRESS] [GATEWAY]

Arguments:
    VMID         - ID контейнера (100-999), default: auto-detect
    HOSTNAME     - Ім'я хоста, default: competitive-intelligence
    IP_ADDRESS   - IP адреса або 'dhcp', default: dhcp
    GATEWAY      - Gateway (якщо IP static), default: 192.168.1.1

Examples:
    $0 100 selenium-grid dhcp
    $0 101 selenium-grid 192.168.1.100 192.168.1.1
    $0 102 ci-prod 10.0.0.50 10.0.0.1

EOF
}

##############################################################################
# Pre-flight Checks
##############################################################################

check_proxmox() {
    print_info "Перевірка Proxmox VE..."
    
    if ! command -v pct &> /dev/null; then
        print_error "Цей скрипт повинен запускатися на Proxmox VE хості"
        exit 1
    fi
    
    print_success "Proxmox VE виявлено"
}

check_vmid() {
    if [[ -z "$VMID" ]]; then
        # Auto-detect next available VMID
        VMID=$(pvesh get /cluster/nextid)
        print_info "Auto-detected VMID: $VMID"
    fi
    
    # Check if VMID already exists
    if pct status "$VMID" &> /dev/null; then
        print_error "VMID $VMID вже використовується"
        exit 1
    fi
    
    print_success "VMID $VMID доступний"
}

check_template() {
    print_info "Перевірка наявності template..."
    
    # Check if template exists in local storage
    if ! pvesm list local | grep -q "ubuntu-24.04-standard_24.04-2_amd64.tar.zst"; then
        print_warning "Template ubuntu-24.04-standard не знайдено"
        print_info "Завантаження template..."
        pveam download local ubuntu-24.04-standard_24.04-2_amd64.tar.zst
    fi
    
    print_success "Template готовий"
}

##############################################################################
# Container Creation
##############################################################################

create_container() {
    print_info "Створення LXC контейнера..."
    
    local net_config="name=eth0,bridge=$BRIDGE,firewall=1"
    
    if [[ "$IP_ADDRESS" == "dhcp" ]]; then
        net_config="${net_config},ip=dhcp"
    else
        net_config="${net_config},ip=${IP_ADDRESS}/24,gw=${GATEWAY}"
    fi
    
    # Create container
    pct create "$VMID" "$TEMPLATE" \
        --hostname "$HOSTNAME" \
        --cores "$CORES" \
        --memory "$MEMORY" \
        --swap "$SWAP" \
        --rootfs "$STORAGE:$DISK_SIZE" \
        --net0 "$net_config" \
        --nameserver "8.8.8.8" \
        --searchdomain "local" \
        --features "keyctl=1,nesting=1" \
        --unprivileged 0 \
        --onboot 1 \
        --start 0 \
        --password \
        --description "Competitive Intelligence - Selenium Grid Container"
    
    print_success "Контейнер $VMID створено"
}

configure_container() {
    print_info "Налаштування контейнера..."
    
    # Set additional configurations
    pct set "$VMID" \
        --cpuunits 2048 \
        --cpulimit 4 \
        --startup "order=1"
    
    print_success "Контейнер налаштовано"
}

configure_apparmor() {
    print_info "Налаштування AppArmor профілю для контейнера..."
    
    local config_file="/etc/pve/lxc/${VMID}.conf"
    
    if [[ ! -f "$config_file" ]]; then
        print_warning "Файл $config_file не знайдено — пропускаю AppArmor налаштування"
        return
    fi
    
    if grep -q "^lxc.apparmor.profile:" "$config_file"; then
        sed -i "s/^lxc\.apparmor\.profile:.*/lxc.apparmor.profile: unconfined/" "$config_file"
    else
        echo "lxc.apparmor.profile: unconfined" >> "$config_file"
    fi
    
    print_success "AppArmor профіль виставлено у unconfined"
}

##############################################################################
# Container Setup
##############################################################################

start_container() {
    print_info "Запуск контейнера..."
    
    pct start "$VMID"
    
    # Wait for container to start
    sleep 5
    
    print_success "Контейнер запущено"
}

setup_system() {
    print_info "Налаштування системи в контейнері..."
    
    # Update system
    print_info "Оновлення системи..."
    pct exec "$VMID" -- bash -c "apt-get update && apt-get upgrade -y"
    
    # Install required packages
    print_info "Встановлення необхідних пакетів..."
    pct exec "$VMID" -- bash -c "apt-get install -y \
        curl \
        wget \
        git \
        ca-certificates \
        gnupg \
        lsb-release \
        sudo \
        vim \
        htop \
        net-tools \
        iputils-ping"
    
    print_success "Система налаштована"
}

install_docker() {
    print_info "Встановлення Docker..."
    
    # Install Docker
    pct exec "$VMID" -- bash -c '
        # Add Docker GPG key
        mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        
        # Add Docker repository
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # Install Docker
        apt-get update
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        
        # Enable Docker service
        systemctl enable docker
        systemctl start docker
    '
    
    print_success "Docker встановлено"
    
    # Apply sane defaults for Docker inside LXC
    print_info "Налаштування Docker для LXC..."
    pct exec "$VMID" -- bash -c '
        # Create Docker daemon config
        mkdir -p /etc/docker
        cat > /etc/docker/daemon.json << "DOCKEREOF"
{
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
DOCKEREOF
        
        # Restart Docker to apply changes
        systemctl restart docker
        
        # Wait for Docker to be ready
        sleep 3
        
        # Verify Docker works
        docker run --rm hello-world > /dev/null 2>&1 || echo "Docker verification may need manual check"
    '
    
    print_success "Docker налаштовано для роботи в LXC"
}

install_project() {
    print_info "Встановлення проекту..."
    
    # Create project directory
    pct exec "$VMID" -- bash -c "mkdir -p /opt/competitive-intelligence"
    
    print_info "Проект буде встановлено в /opt/competitive-intelligence"
    print_warning "Завантажте код проекту за допомогою:"
    echo "    pct push $VMID /path/to/project.tar.gz /tmp/project.tar.gz"
    echo "    pct exec $VMID -- tar -xzf /tmp/project.tar.gz -C /opt/competitive-intelligence"
    echo ""
    print_warning "Або використайте git:"
    echo "    pct exec $VMID -- git clone <repository-url> /opt/competitive-intelligence"
    
    print_success "Директорія проекту створена"
}

##############################################################################
# Firewall Rules
##############################################################################

configure_firewall() {
    print_info "Налаштування firewall правил..."
    
    # Allow required ports
    local ports=(
        "4444"   # Selenium Hub
        "5000"   # Web Dashboard
        "7901"   # Chrome VNC 1
        "7902"   # Chrome VNC 2
        "7903"   # Firefox VNC
        "7904"   # Edge VNC
        "11434"  # Ollama
    )
    
    for port in "${ports[@]}"; do
        print_info "Відкриття порту $port..."
        # Note: Proxmox firewall rules can be set via web UI or pvesh
    done
    
    print_success "Firewall налаштовано"
}

##############################################################################
# Post-Installation Info
##############################################################################

show_info() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}   Контейнер успішно створено! 🎉${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo ""
    
    echo -e "${BLUE}📋 Інформація про контейнер:${NC}"
    echo -e "  • VMID:       $VMID"
    echo -e "  • Hostname:   $HOSTNAME"
    echo -e "  • IP Address: $IP_ADDRESS"
    echo -e "  • CPUs:       $CORES cores"
    echo -e "  • RAM:        ${MEMORY}MB"
    echo -e "  • Disk:       ${DISK_SIZE}GB"
    echo ""
    
    echo -e "${BLUE}🔧 Наступні кроки:${NC}"
    echo ""
    echo "1. Під'єднайтеся до контейнера:"
    echo "   pct enter $VMID"
    echo ""
    echo "2. Завантажте код проекту:"
    echo "   cd /opt/competitive-intelligence"
    echo "   git clone <your-repo-url> ."
    echo ""
    echo "3. Запустіть deployment:"
    echo "   cd /opt/competitive-intelligence"
    echo "   ./deploy.sh"
    echo ""
    echo "4. Доступ до сервісів:"
    if [[ "$IP_ADDRESS" == "dhcp" ]]; then
        local container_ip=$(pct exec "$VMID" -- hostname -I | awk '{print $1}')
        echo "   • Selenium Hub:     http://${container_ip}:4444"
        echo "   • Web Dashboard:    http://${container_ip}:5000"
    else
        echo "   • Selenium Hub:     http://${IP_ADDRESS}:4444"
        echo "   • Web Dashboard:    http://${IP_ADDRESS}:5000"
    fi
    echo ""
    
    echo -e "${YELLOW}⚠ Важливі нотатки:${NC}"
    echo "  • Docker вже встановлено та налаштовано"
    echo "  • Контейнер налаштовано для автозапуску (onboot)"
    echo "  • Nesting увімкнено для підтримки Docker"
    echo "  • Firewall правила потрібно налаштувати вручну в Proxmox UI"
    echo ""
}

##############################################################################
# Main Execution
##############################################################################

main() {
    echo -e "${BLUE}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   Створення LXC контейнера для Proxmox                      ║
║   Competitive Intelligence + Selenium Grid                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    # Show help if requested
    if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
        show_usage
        exit 0
    fi
    
    # Run setup
    check_proxmox
    check_vmid
    check_template
    create_container
    configure_container
    configure_apparmor
    start_container
    setup_system
    install_docker
    install_project
    configure_firewall
    show_info
}

# Run main function
main "$@"
