#!/bin/bash

##############################################################################
# scale-browsers.sh - Dynamic Browser Scaling Script
#
# Динамічне масштабування браузерних нод у Selenium Grid
# Дозволяє додавати або видаляти браузерні контейнери на льоту
#
# Використання:
#   ./scale-browsers.sh chrome 5        # Масштабувати Chrome до 5 нод
#   ./scale-browsers.sh firefox 3       # Масштабувати Firefox до 3 нод
#   ./scale-browsers.sh edge 2          # Масштабувати Edge до 2 нод
#   ./scale-browsers.sh --status        # Показати поточний стан
#   ./scale-browsers.sh --auto          # Автоматичне масштабування
##############################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.proxmox.yml"
PROJECT_NAME="competitive-intelligence"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Docker compose command
DOCKER_COMPOSE_CMD=""

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
    echo -e "${CYAN}ℹ $1${NC}"
}

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
}

##############################################################################
# Docker Setup
##############################################################################

detect_docker_compose() {
    if docker compose version &> /dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    else
        print_error "Docker Compose не знайдено"
        exit 1
    fi
}

##############################################################################
# Browser Node Management
##############################################################################

get_current_nodes() {
    local browser=$1
    local count=$(docker ps --filter "name=selenium-${browser}" --format "{{.Names}}" | wc -l)
    echo "$count"
}

create_browser_node() {
    local browser=$1
    local node_id=$2
    local vnc_port=$((7900 + node_id))
    local novnc_port=$((5900 + node_id))
    
    print_info "Створення $browser node $node_id..."
    
    # Determine image based on browser
    local image=""
    case $browser in
        chrome)
            image="selenium/node-chrome:4.26.0"
            ;;
        firefox)
            image="selenium/node-firefox:4.26.0"
            ;;
        edge)
            image="selenium/node-edge:4.26.0"
            ;;
        *)
            print_error "Невідомий браузер: $browser"
            return 1
            ;;
    esac
    
    # Create container
    docker run -d \
        --name "selenium-${browser}-${node_id}" \
        --network selenium-grid \
        --shm-size 2g \
        -e SE_EVENT_BUS_HOST=selenium-hub \
        -e SE_EVENT_BUS_PUBLISH_PORT=4442 \
        -e SE_EVENT_BUS_SUBSCRIBE_PORT=4443 \
        -e SE_NODE_MAX_SESSIONS=3 \
        -e SE_NODE_SESSION_TIMEOUT=300 \
        -e SE_VNC_NO_PASSWORD=1 \
        -e SE_SCREEN_WIDTH=1920 \
        -e SE_SCREEN_HEIGHT=1080 \
        -e SE_NODE_GRID_URL=http://selenium-hub:4444 \
        -p "${vnc_port}:7900" \
        -p "${novnc_port}:5900" \
        -v /dev/shm:/dev/shm \
        --restart unless-stopped \
        --label "com.proxmox.service=${browser}-node" \
        --label "com.proxmox.node_id=${node_id}" \
        --label "com.proxmox.browser=${browser}" \
        "$image"
    
    print_success "$browser node $node_id створено (VNC: $vnc_port, noVNC: $novnc_port)"
}

remove_browser_node() {
    local browser=$1
    local node_id=$2
    
    print_info "Видалення $browser node $node_id..."
    
    if docker stop "selenium-${browser}-${node_id}" &> /dev/null; then
        docker rm "selenium-${browser}-${node_id}" &> /dev/null
        print_success "$browser node $node_id видалено"
    else
        print_warning "$browser node $node_id не знайдено або вже видалено"
    fi
}

scale_browser() {
    local browser=$1
    local target_count=$2
    
    print_header "Масштабування $browser до $target_count нод"
    
    local current_count=$(get_current_nodes "$browser")
    print_info "Поточна кількість $browser нод: $current_count"
    
    if [[ $target_count -eq $current_count ]]; then
        print_info "Кількість нод вже відповідає цільовій"
        return 0
    elif [[ $target_count -gt $current_count ]]; then
        # Scale up
        local nodes_to_add=$((target_count - current_count))
        print_info "Додаємо $nodes_to_add нод..."
        
        for ((i=current_count+1; i<=target_count; i++)); do
            create_browser_node "$browser" "$i"
            sleep 2
        done
    else
        # Scale down
        local nodes_to_remove=$((current_count - target_count))
        print_info "Видаляємо $nodes_to_remove нод..."
        
        for ((i=current_count; i>target_count; i--)); do
            remove_browser_node "$browser" "$i"
        done
    fi
    
    print_success "Масштабування завершено"
    
    # Wait for nodes to register
    print_info "Очікування реєстрації нод у Grid..."
    sleep 5
    
    show_grid_status
}

##############################################################################
# Status & Monitoring
##############################################################################

show_grid_status() {
    print_header "Статус Selenium Grid"
    
    # Check if hub is running
    if ! docker exec selenium-hub curl -f http://localhost:4444/wd/hub/status &> /dev/null; then
        print_error "Selenium Hub не відповідає"
        return 1
    fi
    
    # Get grid status
    local grid_status=$(docker exec selenium-hub curl -s http://localhost:4444/wd/hub/status)
    
    # Parse and display node information
    echo ""
    print_info "Зареєстровані ноди:"
    
    for browser in chrome firefox edge; do
        local count=$(get_current_nodes "$browser")
        echo -e "  • ${browser^}: ${GREEN}$count${NC} нод"
        
        # List individual nodes
        docker ps --filter "name=selenium-${browser}" --format "    - {{.Names}} ({{.Status}})" | sed "s/^/  /"
    done
    
    echo ""
    print_info "Детальний статус Grid:"
    echo "$grid_status" | python3 -m json.tool 2>/dev/null || echo "$grid_status"
}

show_node_metrics() {
    print_header "Метрики браузерних нод"
    
    echo ""
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
        $(docker ps --filter "label=com.proxmox.service" --filter "name=selenium-" --format "{{.Names}}")
}

##############################################################################
# Auto-scaling
##############################################################################

auto_scale() {
    print_header "Автоматичне масштабування"
    
    print_info "Аналіз навантаження Grid..."
    
    # Get current sessions
    local grid_status=$(docker exec selenium-hub curl -s http://localhost:4444/wd/hub/status)
    
    # This is a simplified example - in production, you'd want more sophisticated logic
    print_warning "Автоматичне масштабування у розробці"
    print_info "Використовуйте ручне масштабування: ./scale-browsers.sh <browser> <count>"
}

##############################################################################
# Cleanup
##############################################################################

cleanup_dead_nodes() {
    print_header "Очищення мертвих нод"
    
    print_info "Пошук та видалення неактивних контейнерів..."
    
    local removed_count=0
    for container in $(docker ps -a --filter "label=com.proxmox.service" --filter "status=exited" --format "{{.Names}}"); do
        docker rm "$container"
        print_success "Видалено: $container"
        removed_count=$((removed_count + 1))
    done
    
    if [[ $removed_count -eq 0 ]]; then
        print_info "Мертвих нод не знайдено"
    else
        print_success "Видалено $removed_count мертвих нод"
    fi
}

##############################################################################
# Usage
##############################################################################

show_usage() {
    cat << EOF
Usage: $0 <browser> <count>
       $0 --status
       $0 --auto
       $0 --metrics
       $0 --cleanup

Масштабування браузерних нод у Selenium Grid

Arguments:
    <browser>    - Тип браузера (chrome, firefox, edge)
    <count>      - Цільова кількість нод (1-99)

Options:
    --status     - Показати поточний статус Grid
    --metrics    - Показати метрики нод
    --auto       - Автоматичне масштабування
    --cleanup    - Видалити мертві контейнери
    --help, -h   - Показати це повідомлення

Examples:
    $0 chrome 5          # Масштабувати Chrome до 5 нод
    $0 firefox 3         # Масштабувати Firefox до 3 нод
    $0 edge 2            # Масштабувати Edge до 2 нод
    $0 --status          # Показати статус
    $0 --metrics         # Показати метрики

Notes:
    • Кожна нода може обробляти до 3 одночасних сесій
    • Кожна нода вимагає ~2GB RAM
    • VNC порти призначаються автоматично (7901+)
    • noVNC порти призначаються автоматично (5901+)

EOF
}

##############################################################################
# Main
##############################################################################

main() {
    # Detect docker compose command
    detect_docker_compose
    
    # Parse arguments
    case "${1:-}" in
        --help|-h)
            show_usage
            exit 0
            ;;
        --status)
            show_grid_status
            exit 0
            ;;
        --metrics)
            show_node_metrics
            exit 0
            ;;
        --auto)
            auto_scale
            exit 0
            ;;
        --cleanup)
            cleanup_dead_nodes
            exit 0
            ;;
        chrome|firefox|edge)
            local browser=$1
            local count=${2:-}
            
            if [[ -z "$count" ]] || ! [[ "$count" =~ ^[0-9]+$ ]]; then
                print_error "Невірна кількість нод"
                show_usage
                exit 1
            fi
            
            if [[ $count -lt 0 ]] || [[ $count -gt 99 ]]; then
                print_error "Кількість нод повинна бути від 0 до 99"
                exit 1
            fi
            
            scale_browser "$browser" "$count"
            ;;
        "")
            print_error "Відсутні аргументи"
            show_usage
            exit 1
            ;;
        *)
            print_error "Невідома опція: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main
main "$@"
