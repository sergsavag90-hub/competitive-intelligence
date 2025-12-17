#!/bin/bash

##############################################################################
# deploy.sh - Automated Deployment Script for Proxmox
# 
# This script handles complete deployment from start to finish:
# - Prerequisites check
# - Docker installation
# - Project setup
# - Container deployment
# - Health checks
# - Monitoring setup
#
# Usage: 
#   ./deploy.sh                    # Full deployment
#   ./deploy.sh --update           # Update existing deployment
#   ./deploy.sh --scale chrome=5   # Scale Chrome nodes to 5
#   ./deploy.sh --stop             # Stop all services
#   ./deploy.sh --cleanup          # Remove all containers and data
#
##############################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="competitive-intelligence"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.proxmox.yml"
LOG_FILE="${SCRIPT_DIR}/deploy.log"
ENV_FILE="${SCRIPT_DIR}/.env"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Docker compose command detection
DOCKER_COMPOSE_CMD=""

##############################################################################
# Utility Functions
##############################################################################

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "$LOG_FILE"
}

print_banner() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🚀 Competitive Intelligence - Proxmox Deployment          ║
║                                                              ║
║   Автоматичне розгортання Selenium Grid + Intelligence      ║
║   Tool у Proxmox середовищі                                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    log "INFO" "$1"
}

print_error() {
    echo -e "${RED}✗ $1${NC}" >&2
    log "ERROR" "$1"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
    log "WARN" "$1"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

confirm() {
    local prompt="$1"
    local default="${2:-n}"
    
    if [[ "$default" == "y" ]]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi
    
    read -p "$prompt" -n 1 -r
    echo
    
    if [[ "$default" == "y" ]]; then
        [[ $REPLY =~ ^[Nn]$ ]] && return 1 || return 0
    else
        [[ $REPLY =~ ^[Yy]$ ]] && return 0 || return 1
    fi
}

##############################################################################
# Prerequisites Check
##############################################################################

check_system() {
    print_header "Перевірка системних вимог"
    
    # Check if running on Linux
    if [[ "$(uname -s)" != "Linux" ]]; then
        print_error "Цей скрипт підтримує тільки Linux системи"
        exit 1
    fi
    print_success "Операційна система: Linux"
    
    # Check available memory
    local total_mem=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $total_mem -lt 4 ]]; then
        print_warning "Рекомендується мінімум 4GB RAM (знайдено: ${total_mem}GB)"
    else
        print_success "Доступна память: ${total_mem}GB"
    fi
    
    # Check disk space
    local disk_space=$(df -BG "$SCRIPT_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ $disk_space -lt 10 ]]; then
        print_warning "Рекомендується мінімум 10GB вільного місця (знайдено: ${disk_space}GB)"
    else
        print_success "Доступне місце на диску: ${disk_space}GB"
    fi
    
    # Check CPU cores
    local cpu_cores=$(nproc)
    print_info "Кількість CPU ядер: ${cpu_cores}"
}

check_docker() {
    print_header "Перевірка Docker"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker не знайдено. Будь ласка, встановіть Docker перед запуском."
        exit 1
    else
        local docker_version=$(docker --version | awk '{print $3}' | sed 's/,//')
        print_success "Docker встановлено: $docker_version"
    fi
    
    # Docker daemon check is bypassed in this environment as Docker commands still work.
    
    # Detect docker compose command
    if docker compose version &> /dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
        local compose_version=$(docker compose version --short)
        print_success "Docker Compose встановлено: v$compose_version"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
        local compose_version=$(docker-compose --version | awk '{print $3}' | sed 's/,//')
        print_success "Docker Compose встановлено: $compose_version"
    else
        print_error "Docker Compose не знайдено"
        exit 1
    fi
}

install_docker() {
    print_error "Функція встановлення Docker вимкнена. Будь ласка, встановіть Docker вручну."
    exit 1
}

##############################################################################
# Environment Setup
##############################################################################

setup_environment() {
    print_header "Налаштування середовища"
    
    # Create necessary directories
    local dirs=("data" "exports" "logs" "backups")
    for dir in "${dirs[@]}"; do
        if [[ ! -d "$SCRIPT_DIR/$dir" ]]; then
            mkdir -p "$SCRIPT_DIR/$dir"
            print_success "Створено директорію: $dir"
        fi
    done
    
    # Create .env file if not exists
    if [[ ! -f "$ENV_FILE" ]]; then
        print_info "Створення .env файлу..."
        cat > "$ENV_FILE" << 'EOF'
# Competitive Intelligence Environment Configuration

# Project
PROJECT_NAME=competitive-intelligence
COMPOSE_PROJECT_NAME=competitive-intelligence

# Selenium Grid
SELENIUM_HUB_URL=http://selenium-hub:4444/wd/hub
SE_SESSION_TIMEOUT=300
SE_NODE_MAX_SESSIONS=3
GRID_MAX_SESSION=15

# Database
DATABASE_PATH=/data/competitive_intelligence.db

# Ollama LLM
OLLAMA_HOST=http://192.168.1.220:11434
OLLAMA_MODEL=gemma3:4b

# Web Interface
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=false

# Logging
LOG_LEVEL=INFO

# Browser Configuration
CHROME_NODES=2
FIREFOX_NODES=1
EDGE_NODES=1

# Resource Limits
CPU_LIMIT=2
MEMORY_LIMIT=2G
SHM_SIZE=2gb
EOF
        print_success ".env файл створено"
    else
        print_info ".env файл вже існує"
    fi
    
    # Set proper permissions
    chmod 644 "$ENV_FILE"
    chmod 755 "$SCRIPT_DIR"/{data,exports,logs,backups}
}

##############################################################################
# Docker Operations
##############################################################################

pull_images() {
    print_header "Завантаження Docker образів"
    
    print_info "Це може зайняти декілька хвилин..."
    
    if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" pull 2>&1 | tee -a "$LOG_FILE"; then
        print_success "Образи завантажено успішно"
    else
        print_error "Помилка завантаження образів"
        exit 1
    fi
}

build_images() {
    print_header "Збірка Docker образів"
    
    if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" build --no-cache 2>&1 | tee -a "$LOG_FILE"; then
        print_success "Образи зібрано успішно"
    else
        print_error "Помилка збірки образів"
        exit 1
    fi
}

start_services() {
    print_header "Запуск сервісів"
    
    # Примусове видалення старих контейнерів, щоб уникнути конфлікту імен
    print_info "Очищення старих контейнерів (якщо існують)..."
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" down --remove-orphans > /dev/null 2>&1 || true
    
    print_info "Запуск контейнерів..."
    if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" up -d 2>&1 | tee -a "$LOG_FILE"; then
        print_success "Контейнери запущено"
    else
        print_error "Помилка запуску контейнерів"
        exit 1
    fi
    
    # Wait for services to be healthy
    print_info "Очікування готовності сервісів..."
    sleep 10
    
    wait_for_services
}

stop_services() {
    print_header "Зупинка сервісів"
    
    if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" down 2>&1 | tee -a "$LOG_FILE"; then
        print_success "Сервіси зупинено"
    else
        print_error "Помилка зупинки сервісів"
        exit 1
    fi
}

wait_for_services() {
    print_info "Перевірка статусу сервісів..."
    
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if docker exec selenium-hub curl -f http://localhost:4444/wd/hub/status &> /dev/null; then
            print_success "Selenium Hub готовий"
            break
        fi
        
        attempt=$((attempt + 1))
        if [[ $attempt -eq $max_attempts ]]; then
            print_error "Selenium Hub не відповідає після ${max_attempts} спроб"
            exit 1
        fi
        
        sleep 2
    done
    
    # Check web interface
    attempt=0
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -f http://localhost:5000/health &> /dev/null 2>&1; then
            print_success "Web інтерфейс готовий"
            break
        fi
        
        attempt=$((attempt + 1))
        if [[ $attempt -eq $max_attempts ]]; then
            print_warning "Web інтерфейс не відповідає (можливо ще запускається)"
            break
        fi
        
        sleep 2
    done
}

##############################################################################
# Service Management
##############################################################################

show_status() {
    print_header "Статус сервісів"
    
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" ps
    
    echo ""
    print_info "Selenium Grid статус:"
    if docker exec selenium-hub curl -s http://localhost:4444/wd/hub/status | python3 -m json.tool 2>/dev/null; then
        :
    else
        print_warning "Не вдалося отримати статус Selenium Grid"
    fi
}

show_logs() {
    local service="${1:-}"
    
    if [[ -n "$service" ]]; then
        print_header "Логи сервісу: $service"
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" logs --tail=100 -f "$service"
    else
        print_header "Логи всіх сервісів"
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" logs --tail=50 -f
    fi
}

scale_service() {
    local service=$1
    local count=$2
    
    print_header "Масштабування сервісу"
    print_info "Масштабування $service до $count інстансів..."
    
    if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" up -d --scale "$service=$count" 2>&1 | tee -a "$LOG_FILE"; then
        print_success "Масштабування виконано"
    else
        print_error "Помилка масштабування"
        exit 1
    fi
}

##############################################################################
# Health Checks
##############################################################################

run_health_checks() {
    print_header "Перевірка здоров'я системи"
    
    local all_healthy=true
    
    # Check Selenium Hub
    print_info "Перевірка Selenium Hub..."
    if docker exec selenium-hub curl -f http://localhost:4444/wd/hub/status &> /dev/null; then
        print_success "Selenium Hub: ✓ Healthy"
    else
        print_error "Selenium Hub: ✗ Unhealthy"
        all_healthy=false
    fi
    
    # Check browser nodes
    for container in $(docker ps --filter "label=com.proxmox.service" --format "{{.Names}}" | grep "selenium-"); do
        if docker exec "$container" pgrep -f "selenium" &> /dev/null; then
            print_success "$container: ✓ Running"
        else
            print_error "$container: ✗ Not Running"
            all_healthy=false
        fi
    done
    
    # Check web interface
    print_info "Перевірка Web інтерфейсу..."
    if curl -f http://localhost:5000/health &> /dev/null 2>&1; then
        print_success "Web Interface: ✓ Healthy"
    else
        print_warning "Web Interface: ⚠ Not Ready"
    fi
    
    if $all_healthy; then
        print_success "Всі сервіси працюють нормально"
        return 0
    else
        print_warning "Деякі сервіси мають проблеми"
        return 1
    fi
}

##############################################################################
# Backup & Restore
##############################################################################

create_backup() {
    print_header "Створення резервної копії"
    
    local backup_dir="$SCRIPT_DIR/backups"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$backup_dir/backup_${timestamp}.tar.gz"
    
    print_info "Створення backup: $backup_file"
    
    # Create backup
    tar -czf "$backup_file" \
        -C "$SCRIPT_DIR" \
        data/ \
        config.yaml \
        .env \
        2>&1 | tee -a "$LOG_FILE"
    
    if [[ $? -eq 0 ]]; then
        print_success "Backup створено: $backup_file"
        
        # Keep only last 5 backups
        local backup_count=$(ls -1 "$backup_dir"/backup_*.tar.gz 2>/dev/null | wc -l)
        if [[ $backup_count -gt 5 ]]; then
            print_info "Видалення старих backups (залишаємо останні 5)..."
            ls -1t "$backup_dir"/backup_*.tar.gz | tail -n +6 | xargs rm -f
        fi
    else
        print_error "Помилка створення backup"
        exit 1
    fi
}

##############################################################################
# Monitoring & Maintenance
##############################################################################

show_metrics() {
    print_header "Метрики системи"
    
    # Container stats
    print_info "Використання ресурсів контейнерами:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
        $(docker ps --filter "label=com.proxmox.service" --format "{{.Names}}")
    
    echo ""
    
    # Disk usage
    print_info "Використання диску:"
    df -h "$SCRIPT_DIR" | tail -n 1
    
    echo ""
    
    # Database size
    if [[ -f "$SCRIPT_DIR/data/competitive_intelligence.db" ]]; then
        local db_size=$(du -h "$SCRIPT_DIR/data/competitive_intelligence.db" | cut -f1)
        print_info "Розмір бази даних: $db_size"
    fi
}

cleanup_system() {
    print_header "Очищення системи"
    
    if ! confirm "Це видалить всі контейнери, образи та дані. Продовжити?" "n"; then
        print_info "Операцію скасовано"
        return
    fi
    
    # Create final backup
    create_backup
    
    # Stop and remove containers
    print_info "Зупинка та видалення контейнерів..."
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" down -v
    
    # Remove images
    if confirm "Видалити Docker образи?" "n"; then
        print_info "Видалення образів..."
        docker images | grep selenium | awk '{print $3}' | xargs -r docker rmi -f
        docker images | grep competitive-intelligence | awk '{print $3}' | xargs -r docker rmi -f
    fi
    
    # Clean data
    if confirm "Видалити дані (data/, logs/, exports/)?" "n"; then
        print_info "Видалення даних..."
        rm -rf "$SCRIPT_DIR"/{data,logs,exports}/*
    fi
    
    print_success "Очищення завершено"
}

##############################################################################
# Update Operations
##############################################################################

update_deployment() {
    print_header "Оновлення розгортання"
    
    # Create backup before update
    create_backup
    
    # Pull latest images
    print_info "Завантаження останніх образів..."
    pull_images
    
    # Rebuild local images
    print_info "Перебудова локальних образів..."
    build_images
    
    # Restart services
    print_info "Перезапуск сервісів..."
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" up -d --force-recreate
    
    wait_for_services
    
    print_success "Оновлення завершено"
}

##############################################################################
# Information Display
##############################################################################

show_info() {
    print_header "Інформація про розгортання"
    
    echo ""
    echo -e "${CYAN}📊 Доступні сервіси:${NC}"
    echo -e "  • Selenium Grid Hub:    http://localhost:4444"
    echo -e "  • Web Dashboard:        http://localhost:5000"
    echo -e "  • Chrome Node 1 (VNC):  http://localhost:7901"
    echo -e "  • Chrome Node 2 (VNC):  http://localhost:7902"
    echo -e "  • Firefox Node (VNC):   http://localhost:7903"
    echo -e "  • Edge Node (VNC):      http://localhost:7904"
    echo -e "  • Ollama API:           http://localhost:11434"
    
    echo ""
    echo -e "${CYAN}📁 Директорії:${NC}"
    echo -e "  • Дані:         $SCRIPT_DIR/data"
    echo -e "  • Експорти:     $SCRIPT_DIR/exports"
    echo -e "  • Логи:         $SCRIPT_DIR/logs"
    echo -e "  • Backups:      $SCRIPT_DIR/backups"
    
    echo ""
    echo -e "${CYAN}🔧 Корисні команди:${NC}"
    echo -e "  • Статус:       ./deploy.sh --status"
    echo -e "  • Логи:         ./deploy.sh --logs [service]"
    echo -e "  • Зупинити:     ./deploy.sh --stop"
    echo -e "  • Restart:      ./deploy.sh --restart"
    echo -e "  • Backup:       ./deploy.sh --backup"
    echo -e "  • Оновити:      ./deploy.sh --update"
    echo -e "  • Масштабування: ./deploy.sh --scale chrome-node=5"
    echo ""
}

##############################################################################
# Main Deployment
##############################################################################

full_deploy() {
    print_banner
    
    log "INFO" "Starting full deployment at $(date)"
    
    check_system
    check_docker
    setup_environment
    stop_services || true # Видаляємо старі контейнери, якщо вони є
    pull_images
    build_images
    start_services
    run_health_checks
    show_info
    
    print_header "Розгортання завершено успішно! 🎉"
    
    log "INFO" "Deployment completed successfully"
}

##############################################################################
# Command Line Interface
##############################################################################

show_usage() {
    cat << EOF
Usage: $0 [OPTION]

Automated deployment script for Competitive Intelligence на Proxmox

Options:
    (no args)           Повне розгортання (full deploy)
    --help, -h          Показати це повідомлення
    --status            Показати статус сервісів
    --logs [service]    Показати логи (всіх або конкретного сервісу)
    --stop              Зупинити всі сервіси
    --start             Запустити сервіси
    --restart           Перезапустити сервіси
    --update            Оновити розгортання
    --scale SVC=N       Масштабувати сервіс (напр. --scale chrome-node=5)
    --backup            Створити резервну копію
    --metrics           Показати метрики системи
    --health            Виконати health checks
    --cleanup           Видалити всі контейнери та дані
    --info              Показати інформацію про розгортання

Examples:
    $0                              # Повне розгортання
    $0 --status                     # Перевірити статус
    $0 --logs intelligence-web      # Логи web сервісу
    $0 --scale chrome-node-1=3      # Масштабувати Chrome ноди
    $0 --update                     # Оновити систему

EOF
}

##############################################################################
# Main Entry Point
##############################################################################

main() {
    # Initialize log file
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Parse command line arguments
    case "${1:-}" in
        --help|-h)
            show_usage
            exit 0
            ;;
        --status)
            check_docker
            show_status
            ;;
        --logs)
            check_docker
            show_logs "${2:-}"
            ;;
        --stop)
            check_docker
            stop_services
            ;;
        --start)
            check_docker
            start_services
            ;;
        --restart)
            check_docker
            stop_services
            sleep 2
            start_services
            ;;
        --update)
            check_docker
            update_deployment
            ;;
        --scale)
            if [[ -z "${2:-}" ]]; then
                print_error "Usage: $0 --scale SERVICE=COUNT"
                exit 1
            fi
            check_docker
            IFS='=' read -r service count <<< "$2"
            scale_service "$service" "$count"
            ;;
        --backup)
            create_backup
            ;;
        --metrics)
            check_docker
            show_metrics
            ;;
        --health)
            check_docker
            run_health_checks
            ;;
        --cleanup)
            check_docker
            cleanup_system
            ;;
        --info)
            show_info
            ;;
        "")
            # Full deployment
            full_deploy
            ;;
        *)
            print_error "Невідома опція: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
