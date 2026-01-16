#!/bin/bash
# Run E2E test inside Docker container

echo "========================================="
echo "Running E2E Test in Docker Container"
echo "========================================="

# Run the test in the API container
docker compose exec api python test_e2e_deployment.py 2>&1 | tee e2e_test_output.log

# Capture exit code
EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo "========================================="
echo "Test completed with exit code: $EXIT_CODE"
echo "Log saved to: e2e_test_output.log"
echo "========================================="

exit $EXIT_CODE
