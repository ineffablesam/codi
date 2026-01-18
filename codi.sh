#!/bin/bash

# manage_codi.sh - Interactive Docker Management Script for Codi

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NETWORK_NAME="codi-network"
BACKEND_DIR="./codi-backend"

# Function to clear the screen
clear_screen() {
    clear
}

# Function to display the banner
show_banner() {
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${BLUE}   Codi Docker Management System      ${NC}"
    echo -e "${BLUE}=======================================${NC}"
}

# Function to setup the network
setup_network() {
    echo -e "${YELLOW}Checking network: ${NETWORK_NAME}...${NC}"
    if ! docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
        echo -e "${GREEN}Creating network: ${NETWORK_NAME}...${NC}"
        docker network create ${NETWORK_NAME}
    else
        echo -e "${BLUE}Network ${NETWORK_NAME} already exists.${NC}"
    fi
}

# Function to start the backend
start_backend() {
    echo -e "${YELLOW}Starting Codi Backend...${NC}"
    setup_network
    if [ -d "$BACKEND_DIR" ]; then
        cd "$BACKEND_DIR" || exit
        docker compose up -d
        cd - > /dev/null || exit
        echo -e "${GREEN}Backend started successfully.${NC}"
    else
        echo -e "${RED}Error: Backend directory $BACKEND_DIR not found.${NC}"
    fi
}

# Function to stop the backend
stop_backend() {
    echo -e "${YELLOW}Stopping Codi Backend...${NC}"
    if [ -d "$BACKEND_DIR" ]; then
        cd "$BACKEND_DIR" || exit
        docker compose stop
        cd - > /dev/null || exit
        echo -e "${GREEN}Backend stopped.${NC}"
    else
        echo -e "${RED}Error: Backend directory $BACKEND_DIR not found.${NC}"
    fi
}

# Function to restart the backend (with build)
restart_backend() {
    echo -e "${YELLOW}Restarting Codi Backend (with build)...${NC}"
    setup_network
    if [ -d "$BACKEND_DIR" ]; then
        cd "$BACKEND_DIR" || exit
        docker compose down
        docker compose up -d --build
        cd - > /dev/null || exit
        echo -e "${GREEN}Backend restarted with new build.${NC}"
    else
        echo -e "${RED}Error: Backend directory $BACKEND_DIR not found.${NC}"
    fi
}

# Function to refresh api and celery (restart only)
refresh_services() {
    echo -e "${YELLOW}Refreshing API and Celery services...${NC}"
    if [ -d "$BACKEND_DIR" ]; then
        cd "$BACKEND_DIR" || exit
        docker compose restart api celery-worker celery-beat
        cd - > /dev/null || exit
        echo -e "${GREEN}Services refreshed.${NC}"
    else
        echo -e "${RED}Error: Backend directory $BACKEND_DIR not found.${NC}"
    fi
}

# Function to show status
show_status() {
    echo -e "${YELLOW}Current Codi Containers Status:${NC}"
    docker ps --filter "name=codi" --filter "network=${NETWORK_NAME}"
}

# Function to purge EVERYTHING
purge_all() {
    echo -e "${RED}WARNING: This will stop and remove ALL containers, volumes, and networks associated with Codi.${NC}"
    read -p "Are you sure you want to continue? (y/N): " confirm
    if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
        echo -e "${YELLOW}Purging Codi resources...${NC}"
        
        # Stop and remove containers from compose
        if [ -d "$BACKEND_DIR" ]; then
            cd "$BACKEND_DIR" || exit
            docker compose down -v --rmi local
            cd - > /dev/null || exit
        fi

        # Cleanup any dangling codi containers
        local codi_containers=$(docker ps -a --filter "name=codi" -q)
        if [ -n "$codi_containers" ]; then
            echo -e "${YELLOW}Removing dangling Codi containers...${NC}"
            docker rm -f $codi_containers
        fi

        # Cleanup network
        if docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
            echo -e "${YELLOW}Removing network ${NETWORK_NAME}...${NC}"
            docker network rm ${NETWORK_NAME}
        fi

        echo -e "${GREEN}Purge complete. Space reclaimed.${NC}"
    else
        echo -e "${BLUE}Purge cancelled.${NC}"
    fi
}

# Main loop
while true; do
    show_banner
    echo -e "1) ${GREEN}Start Backend${NC}"
    echo -e "2) ${YELLOW}Stop Backend${NC}"
    echo -e "3) ${BLUE}Restart Backend (Rebuild)${NC}"
    echo -e "4) ${BLUE}Refresh API & Celery (Restart Only)${NC}"
    echo -e "5) ${NC}Check Status${NC}"
    echo -e "6) ${YELLOW}Setup Network Only${NC}"
    echo -e "7) ${RED}Purge All (Reclaim Space)${NC}"
    echo -e "q) Exit"
    echo
    read -p "Select an option: " choice

    case $choice in
        1) start_backend ;;
        2) stop_backend ;;
        3) restart_backend ;;
        4) refresh_services ;;
        5) show_status ;;
        6) setup_network ;;
        7) purge_all ;;
        q|Q) echo "Goodbye!"; exit 0 ;;
        *) echo -e "${RED}Invalid option.${NC}" ;;
    esac
    
    echo
    read -p "Press Enter to continue..." pause
    clear_screen
done
