#!/bin/bash
# Run E2E tests inside Docker container
# Supports multiple test types

set -e

echo ""
echo "========================================="
echo "       CODI E2E TEST RUNNER"
echo "========================================="
echo ""

# Function to show menu
show_menu() {
    echo "Select test type:"
    echo ""
    echo "  1) E2E Deployment Test"
    echo "     - Creates project, runs agent, builds & deploys"
    echo ""
    echo "  2) Browser Agent Test"
    echo "     - Tests browser-agent service, screenshots, commands"
    echo ""
    echo "  3) Run Both Tests"
    echo ""
    echo "  0) Exit"
    echo ""
}

# Function to run deployment test
run_deployment_test() {
    echo ""
    echo "========================================="
    echo "Running E2E Deployment Test"
    echo "========================================="
    echo ""
    
    docker compose exec api python test_e2e_deployment.py 2>&1 | tee e2e_deployment_output.log
    return ${PIPESTATUS[0]}
}

# Function to run browser agent test
run_browser_agent_test() {
    echo ""
    echo "========================================="
    echo "Running Browser Agent E2E Test"
    echo "========================================="
    echo ""
    
    # Ensure browser-agent service is running
    echo "Checking browser-agent service..."
    if ! docker compose ps browser-agent | grep -q "running"; then
        echo "Starting browser-agent service..."
        docker compose up -d browser-agent
        echo "Waiting 10 seconds for service to initialize..."
        sleep 10
    else
        echo "browser-agent service is running"
    fi
    echo ""
    
    docker compose exec api python test_e2e_browser_agent.py 2>&1 | tee e2e_browser_agent_output.log
    return ${PIPESTATUS[0]}
}

# Check for command line argument
if [ -n "$1" ]; then
    CHOICE=$1
else
    # Interactive mode
    show_menu
    read -p "Enter choice [1-3, 0 to exit]: " CHOICE
fi

echo ""

case $CHOICE in
    1)
        run_deployment_test
        EXIT_CODE=$?
        ;;
    2)
        run_browser_agent_test
        EXIT_CODE=$?
        ;;
    3)
        echo "Running all E2E tests..."
        echo ""
        
        run_deployment_test
        DEPLOY_CODE=$?
        
        run_browser_agent_test
        BROWSER_CODE=$?
        
        echo ""
        echo "========================================="
        echo "COMBINED TEST RESULTS"
        echo "========================================="
        echo "  Deployment Test: $([ $DEPLOY_CODE -eq 0 ] && echo '✅ PASS' || echo '❌ FAIL')"
        echo "  Browser Agent Test: $([ $BROWSER_CODE -eq 0 ] && echo '✅ PASS' || echo '❌ FAIL')"
        echo "========================================="
        
        [ $DEPLOY_CODE -eq 0 ] && [ $BROWSER_CODE -eq 0 ]
        EXIT_CODE=$?
        ;;
    0)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice: $CHOICE"
        echo "Usage: $0 [1|2|3]"
        echo "  1 = Deployment test"
        echo "  2 = Browser agent test"
        echo "  3 = Both tests"
        exit 1
        ;;
esac

echo ""
echo "========================================="
echo "Test completed with exit code: $EXIT_CODE"
echo "========================================="

exit $EXIT_CODE
