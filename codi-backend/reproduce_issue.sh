#!/bin/bash
echo "Testing Opik endpoints..."

echo "1. Testing /api/v1/opik/traces"
curl -v http://localhost:8000/api/v1/opik/traces

echo -e "\n\n2. Testing /api/v1/opik/projects/6/stats"
curl -v http://localhost:8000/api/v1/opik/projects/6/stats

echo -e "\n\nDone."
