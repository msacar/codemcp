#!/bin/bash
# OpenGrok management script for codemcp

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$SCRIPT_DIR/docker/opengrok"
PROJECT_ROOT="$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_usage() {
    echo "Usage: $0 {start|stop|restart|status|logs|clean|index}"
    echo ""
    echo "Commands:"
    echo "  start    - Start OpenGrok container"
    echo "  stop     - Stop OpenGrok container"
    echo "  restart  - Restart OpenGrok container"
    echo "  status   - Show container status"
    echo "  logs     - Show container logs (follow mode)"
    echo "  clean    - Stop container and remove all data"
    echo "  index    - Force re-index of the project"
    echo ""
    echo "Environment variables:"
    echo "  OPENGROK_WORKSPACE - Path to workspace with multiple projects (default: ~/projects)"
    echo "  OPENGROK_URL - OpenGrok URL (default: http://localhost:8080/source)"
    echo ""
    echo "Example:"
    echo "  # Index multiple projects in ~/projects directory"
    echo "  OPENGROK_WORKSPACE=~/projects $0 start"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi

    if ! docker compose version &> /dev/null && ! docker-compose version &> /dev/null; then
        echo -e "${RED}Error: Docker Compose is not installed${NC}"
        exit 1
    fi
}

get_compose_cmd() {
    if docker compose version &> /dev/null; then
        echo "docker compose"
    else
        echo "docker-compose"
    fi
}

start_opengrok() {
    echo -e "${GREEN}Starting OpenGrok...${NC}"
    cd "$DOCKER_DIR"

    # Set default OPENGROK_WORKSPACE if not provided
    export OPENGROK_WORKSPACE="${OPENGROK_WORKSPACE:-$HOME/projects}"

    # Create workspace directory if it doesn't exist
    if [ ! -d "$OPENGROK_WORKSPACE" ]; then
        echo "Creating workspace directory: $OPENGROK_WORKSPACE"
        mkdir -p "$OPENGROK_WORKSPACE"
    fi

    echo "OpenGrok workspace: $OPENGROK_WORKSPACE"
    echo "Projects found:"
    for project in "$OPENGROK_WORKSPACE"/*; do
        if [ -d "$project/.git" ]; then
            echo "  - $(basename "$project")"
        fi
    done

    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD up -d

    echo -e "${GREEN}OpenGrok started!${NC}"
    echo "Waiting for initial indexing..."
    echo ""
    echo "Web UI: http://localhost:8080/source"
    echo "API: http://localhost:8080/source/api/v1/"
    echo ""
    echo "Use '$0 logs' to monitor indexing progress"
}

stop_opengrok() {
    echo -e "${YELLOW}Stopping OpenGrok...${NC}"
    cd "$DOCKER_DIR"
    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD down
    echo -e "${GREEN}OpenGrok stopped${NC}"
}

restart_opengrok() {
    stop_opengrok
    sleep 2
    start_opengrok
}

show_status() {
    cd "$DOCKER_DIR"
    COMPOSE_CMD=$(get_compose_cmd)
    echo -e "${GREEN}OpenGrok container status:${NC}"
    $COMPOSE_CMD ps

    # Check if API is responding
    echo ""
    echo -n "API Status: "
    if curl -s -f http://localhost:8080/source/api/v1/system/ping > /dev/null 2>&1; then
        echo -e "${GREEN}Available${NC}"
    else
        echo -e "${RED}Not responding${NC}"
    fi
}

show_logs() {
    cd "$DOCKER_DIR"
    COMPOSE_CMD=$(get_compose_cmd)
    echo -e "${GREEN}OpenGrok logs (Ctrl+C to stop):${NC}"
    $COMPOSE_CMD logs -f opengrok
}

clean_data() {
    echo -e "${RED}This will remove all OpenGrok data and indexes!${NC}"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$DOCKER_DIR"
        COMPOSE_CMD=$(get_compose_cmd)
        echo -e "${YELLOW}Stopping container and removing data...${NC}"
        $COMPOSE_CMD down -v
        echo -e "${GREEN}OpenGrok data cleaned${NC}"
    else
        echo "Cancelled"
    fi
}

force_index() {
    echo -e "${YELLOW}Forcing re-index...${NC}"
    cd "$DOCKER_DIR"
    COMPOSE_CMD=$(get_compose_cmd)

    # Restart container to trigger re-index
    $COMPOSE_CMD restart opengrok
    echo -e "${GREEN}Re-indexing started${NC}"
    echo "Use '$0 logs' to monitor progress"
}

# Main script logic
check_docker

case "$1" in
    start)
        start_opengrok
        ;;
    stop)
        stop_opengrok
        ;;
    restart)
        restart_opengrok
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    clean)
        clean_data
        ;;
    index)
        force_index
        ;;
    *)
        print_usage
        exit 1
        ;;
esac
