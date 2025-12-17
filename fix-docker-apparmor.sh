#!/bin/bash

##############################################################################
# fix-docker-apparmor.sh - Виправлення AppArmor для Docker в LXC
#
# Цей скрипт вимикає AppArmor для Docker, що дозволяє йому працювати
# всередині LXC контейнера в Proxmox
#
# Використання:
#   ./fix-docker-apparmor.sh
#
# Примітка: Запускати ВСЕРЕДИНІ LXC контейнера
##############################################################################

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
}

##############################################################################
# Main Functions
##############################################################################

check_environment() {
    print_header "Перевірка середовища"
    
    # Check if running in LXC
    if [[ ! -f /proc/1/environ ]] || ! grep -q "container=lxc" /proc/1/environ 2>/dev/null; then
        print_warning "Схоже, що скрипт не запущено в LXC контейнері"
        read -p "Продовжити? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "LXC контейнер виявлено"
    fi
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker не встановлено. Встановіть Docker перед запуском."
        exit 1
    fi
    print_success "Docker встановлено"
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        print_error "Цей скрипт повинен запускатися з правами root"
        exit 1
    fi
    print_success "Запущено з правами root"
}

backup_config() {
    print_header "Створення резервної копії конфігурації"
    
    if [[ -f /etc/docker/daemon.json ]]; then
        cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)
        print_success "Backup створено: /etc/docker/daemon.json.backup.*"
    else
        print_info "Файл /etc/docker/daemon.json не існує (буде створено новий)"
    fi
}

configure_docker() {
    print_header "Налаштування Docker daemon"
    
    # Create docker directory if not exists
    mkdir -p /etc/docker
    
    # Create or update daemon.json
    print_info "Створення /etc/docker/daemon.json з вимкненим AppArmor..."
    
    cat > /etc/docker/daemon.json << 'EOF'
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
  },
  "security-opts": [
    "apparmor=unconfined"
  ]
}
EOF
    
    print_success "Конфігурацію Docker оновлено"
}

restart_docker() {
    print_header "Перезапуск Docker"
    
    print_info "Зупинка Docker..."
    systemctl stop docker || true
    
    print_info "Запуск Docker..."
    systemctl start docker
    
    # Wait for Docker to be ready
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if docker info &> /dev/null; then
            print_success "Docker успішно перезапущено"
            return 0
        fi
        
        attempt=$((attempt + 1))
        sleep 1
    done
    
    print_error "Docker не запустився після ${max_attempts} секунд"
    return 1
}

verify_configuration() {
    print_header "Перевірка конфігурації"
    
    # Check Docker info
    print_info "Інформація Docker:"
    docker info | grep -E "Storage Driver|Security Options" || true
    
    # Try to run a test container
    print_info "Тестування контейнера..."
    if docker run --rm hello-world &> /dev/null; then
        print_success "Тестовий контейнер успішно запущено"
    else
        print_error "Не вдалося запустити тестовий контейнер"
        return 1
    fi
    
    # Try to build a simple image
    print_info "Тестування збірки образу..."
    local test_dir=$(mktemp -d)
    cat > "$test_dir/Dockerfile" << 'EOF'
FROM alpine:latest
RUN apk add --no-cache bash
EOF
    
    if docker build -t test-build "$test_dir" &> /dev/null; then
        print_success "Збірка образу працює"
        docker rmi test-build &> /dev/null || true
    else
        print_error "Збірка образу не працює"
        docker rmi test-build &> /dev/null || true
        rm -rf "$test_dir"
        return 1
    fi
    
    rm -rf "$test_dir"
}

show_info() {
    print_header "Інформація"
    
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Docker налаштовано для роботи в LXC! ✓           ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    echo -e "${BLUE}📋 Що було зроблено:${NC}"
    echo "  • Вимкнено AppArmor для Docker"
    echo "  • Налаштовано storage driver: overlay2"
    echo "  • Налаштовано логування"
    echo "  • Збільшено ліміти файлових дескрипторів"
    echo ""
    
    echo -e "${BLUE}🔧 Конфігураційні файли:${NC}"
    echo "  • Daemon config: /etc/docker/daemon.json"
    echo "  • Backup config: /etc/docker/daemon.json.backup.*"
    echo ""
    
    echo -e "${BLUE}✅ Наступні кроки:${NC}"
    echo "  1. Запустіть deployment:"
    echo "     cd /opt/competitive-intelligence"
    echo "     ./deploy.sh"
    echo ""
    echo "  2. Або використайте docker compose:"
    echo "     docker compose -f docker-compose.proxmox.yml up -d"
    echo ""
    
    echo -e "${YELLOW}⚠ Важливо:${NC}"
    echo "  • Цю конфігурацію потрібно застосовувати лише в LXC контейнерах"
    echo "  • На хост-системі Proxmox AppArmor НЕ слід вимикати"
    echo "  • Регулярно робіть backup даних"
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
║   Виправлення Docker AppArmor для LXC                       ║
║   Competitive Intelligence Tool                             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    check_environment
    backup_config
    configure_docker
    restart_docker
    verify_configuration
    show_info
    
    print_success "Налаштування завершено успішно! 🎉"
}

# Run main function
main "$@"
