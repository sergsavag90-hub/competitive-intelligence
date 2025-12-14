#!/bin/bash

##############################################################################
# start-project.sh
# Automatic project setup and startup script using Docker
# 
# This script handles the complete setup and initialization of the
# competitive-intelligence project using Docker containers.
#
# Usage: ./start-project.sh
# Make executable: chmod +x start-project.sh
##############################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="competitive-intelligence"
DOCKER_COMPOSE_FILE="docker-compose.yml"
SELENIUM_COMPOSE_FILE="docker-compose.selenium.yml"
LOG_FILE="project-startup.log"
DOCKER_COMPOSE_BASE_CMD=""
DOCKER_COMPOSE_DISPLAY_CMD=""
DOCKER_COMPOSE_ARGS=()

##############################################################################
# Utility Functions
##############################################################################

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

docker_compose_run() {
    if [ -z "$DOCKER_COMPOSE_BASE_CMD" ]; then
        print_error "Docker Compose command is not configured. Run check_prerequisites first."
        exit 1
    fi

    if [ "$DOCKER_COMPOSE_BASE_CMD" = "docker-compose" ]; then
        docker-compose "${DOCKER_COMPOSE_ARGS[@]}" "$@"
    else
        docker compose "${DOCKER_COMPOSE_ARGS[@]}" "$@"
    fi
}

##############################################################################
# Pre-flight Checks
##############################################################################

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        log_message "ERROR: Docker not found"
        exit 1
    fi
    print_success "Docker is installed"
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        log_message "ERROR: Docker daemon not running"
        exit 1
    fi
    print_success "Docker daemon is running"
    
    # Check if docker-compose is available
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_BASE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        DOCKER_COMPOSE_BASE_CMD="docker compose"
    else
        print_error "docker-compose is not installed. Please install docker-compose."
        log_message "ERROR: docker-compose not found"
        exit 1
    fi
    DOCKER_COMPOSE_ARGS=("-f" "$DOCKER_COMPOSE_FILE" "-f" "$SELENIUM_COMPOSE_FILE")
    DOCKER_COMPOSE_DISPLAY_CMD="$DOCKER_COMPOSE_BASE_CMD -f $DOCKER_COMPOSE_FILE -f $SELENIUM_COMPOSE_FILE"
    print_success "docker-compose is available (${DOCKER_COMPOSE_BASE_CMD})"
    
    # Check if docker-compose.yml exists
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        print_error "docker-compose.yml not found in current directory"
        log_message "ERROR: docker-compose.yml not found"
        exit 1
    fi
    print_success "docker-compose.yml found"

    if [ ! -f "$SELENIUM_COMPOSE_FILE" ]; then
        print_error "$SELENIUM_COMPOSE_FILE not found in current directory"
        log_message "ERROR: $SELENIUM_COMPOSE_FILE not found"
        exit 1
    fi
    print_success "$SELENIUM_COMPOSE_FILE found"
    
    # Check for .env file
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            print_info "Creating .env file from .env.example..."
            cp .env.example .env
            print_success ".env created from .env.example"
            log_message "INFO: .env created from .env.example"
        else
            print_warning ".env file not found and no .env.example available. Generating default .env configuration."
            cat <<'EOF' > .env
PROJECT_NAME=competitive-intelligence
SELENIUM_HUB_URL=http://selenium-hub:4444/wd/hub
DATABASE_PATH=/data/competitive_intelligence.db
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2
WEB_HOST=0.0.0.0
WEB_PORT=5000
EOF
            print_success "Default .env created"
            log_message "WARNING: .env generated with default values"
        fi
    else
        print_success ".env file exists"
    fi
}

##############################################################################
# Docker Setup
##############################################################################

build_images() {
    print_header "Building Docker Images"
    
    print_info "Building images with docker-compose (selenium grid included)..."
    log_message "INFO: Starting Docker image build"
    
    if docker_compose_run build --no-cache 2>&1 | tee -a "$LOG_FILE"; then
        print_success "Docker images built successfully"
        log_message "INFO: Docker images built successfully"
    else
        print_error "Failed to build Docker images"
        log_message "ERROR: Docker image build failed"
        exit 1
    fi
}

start_containers() {
    print_header "Starting Docker Containers"
    
    print_info "Starting all services..."
    log_message "INFO: Starting Docker containers"
    
    if docker_compose_run up -d 2>&1 | tee -a "$LOG_FILE"; then
        print_success "Docker containers started successfully"
        log_message "INFO: Docker containers started"
    else
        print_error "Failed to start Docker containers"
        log_message "ERROR: Failed to start Docker containers"
        exit 1
    fi
}

wait_for_services() {
    print_header "Waiting for Services to Be Ready"
    
    print_info "Waiting 10 seconds for services to stabilize..."
    sleep 10
    
    log_message "INFO: Services startup check"
    
    # Check if containers are running
    if docker_compose_run ps | grep -q "Up"; then
        print_success "Services are running"
        log_message "INFO: Services are running"
    else
        print_error "Some services failed to start"
        log_message "ERROR: Services failed to start"
        docker_compose_run logs
        exit 1
    fi
}

##############################################################################
# Project Initialization
##############################################################################

initialize_project() {
    print_header "Initializing Project"
    
    log_message "INFO: Running project initialization"
    
    # Add any database migrations, seed scripts, or initialization steps here
    # Example:
    # print_info "Running database migrations..."
    # docker-compose exec -T app npm run migrate
    # print_success "Database migrations completed"
    
    print_info "Project initialization complete"
    log_message "INFO: Project initialization complete"
}

##############################################################################
# Post-Startup Information
##############################################################################

display_startup_info() {
    print_header "Project Setup Complete"
    
    print_success "The $PROJECT_NAME project is now running!"
    echo ""
    
    print_info "Docker Containers Status:"
    docker_compose_run ps
    echo ""
    
    print_info "Useful Commands:"
    echo "  • View logs:           $DOCKER_COMPOSE_DISPLAY_CMD logs -f"
    echo "  • Stop containers:     $DOCKER_COMPOSE_DISPLAY_CMD down"
    echo "  • Restart containers:  $DOCKER_COMPOSE_DISPLAY_CMD restart"
    echo "  • Execute command:     $DOCKER_COMPOSE_DISPLAY_CMD exec <service> <command>"
    echo ""
    
    print_info "Log file: $LOG_FILE"
    
    log_message "INFO: Project startup completed successfully"
}

##############################################################################
# Cleanup on Error
##############################################################################

cleanup_on_error() {
    print_error "An error occurred during setup. Attempting cleanup..."
    log_message "ERROR: Setup failed, initiating cleanup"
    if [ -n "$DOCKER_COMPOSE_BASE_CMD" ]; then
        docker_compose_run down || true
    fi
    print_error "Cleanup completed. Please check $LOG_FILE for details."
    exit 1
}

trap cleanup_on_error ERR

##############################################################################
# Main Execution Flow
##############################################################################

main() {
    clear
    
    echo ""
    print_header "Starting $PROJECT_NAME Setup"
    echo ""
    log_message "INFO: Project startup initiated at $(date '+%Y-%m-%d %H:%M:%S')"
    
    # Execute setup steps
    check_prerequisites
    build_images
    start_containers
    wait_for_services
    initialize_project
    display_startup_info
    
    echo ""
    print_success "All done! Your project is ready to go."
    echo ""
}

# Run main function
main
