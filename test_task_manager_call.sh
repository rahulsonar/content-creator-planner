#!/bin/bash
# Test if task manager can be called and uses Claude properly

echo "Testing Task Manager with Claude..."
echo ""

# Get user token (assuming admin user)
echo "1. Testing task manager call via API..."
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-Internal-Secret: dev-secret-change-in-production" \
  -d '{
    "message": "Create 2 tasks: Task A - Test task one, Task B - Test task two",
    "userId": "cmk42e86r0000p4nyup3t11xg",
    "conversationId": null
  }' | jq -r '.message' | head -50

echo ""
echo "2. Checking recent logs for task manager calls..."
docker logs content-planner-python 2>&1 | grep -E "task_manager|TASK_MANAGER|Claude" | tail -20
