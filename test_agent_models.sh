#!/bin/bash
# Test Agent Model Configuration
# This script tests that each agent is using the correct model from environment variables

echo "=== Agent Model Configuration Test ==="
echo ""

# Check environment variables in the Python container
echo "1. Checking environment variables in python-agents container:"
docker exec content-planner-python env | grep -E "(PLANNER_MODEL|TASK_MANAGER_MODEL|CONTEXT_MANAGER_MODEL)" || echo "Using defaults (gpt-4 for all)"

echo ""
echo "2. Checking settings.py configuration:"
docker exec content-planner-python python3 -c "from config.settings import settings; print(f'PLANNER_MODEL: {settings.PLANNER_MODEL}'); print(f'TASK_MANAGER_MODEL: {settings.TASK_MANAGER_MODEL}'); print(f'CONTEXT_MANAGER_MODEL: {settings.CONTEXT_MANAGER_MODEL}')"

echo ""
echo "=== Test Complete ==="
echo ""
echo "To customize models, add to your .env file:"
echo "  PLANNER_MODEL=gpt-4o"
echo "  TASK_MANAGER_MODEL=gpt-3.5-turbo"
echo "  CONTEXT_MANAGER_MODEL=gpt-4"
echo ""
echo "Then restart: docker compose restart python-agents"
