#!/bin/bash

# Test script for dummy AI mode
# Usage: ./test_dummy_ai.sh

echo "=========================================="
echo "Testing Dummy AI Mode"
echo "=========================================="
echo ""

# Test 1: Greeting
echo "Test 1: Sending greeting message..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/planning/chat \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test-user" \
  -H "X-Internal-Secret: dev-secret-change-in-production" \
  -d '{"message": "Hello!", "conversationId": null}')

echo "Response:"
echo "$RESPONSE" | jq '.'
echo ""
echo "Model used: $(echo "$RESPONSE" | jq -r '.model')"
echo ""

# Test 2: Task planning
echo "=========================================="
echo "Test 2: Sending task planning request..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/planning/chat \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test-user" \
  -H "X-Internal-Secret: dev-secret-change-in-production" \
  -d '{"message": "Help me plan a YouTube video project", "conversationId": null}')

echo "Response:"
echo "$RESPONSE" | jq -r '.message'
echo ""
echo "Model used: $(echo "$RESPONSE" | jq -r '.model')"
echo ""

# Test 3: Help request
echo "=========================================="
echo "Test 3: Sending help request..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/planning/chat \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test-user" \
  -H "X-Internal-Secret: dev-secret-change-in-production" \
  -d '{"message": "What can you help me with?", "conversationId": null}')

echo "Response:"
echo "$RESPONSE" | jq -r '.message'
echo ""
echo "Model used: $(echo "$RESPONSE" | jq -r '.model')"
echo ""

echo "=========================================="
echo "Testing Complete!"
echo "=========================================="
echo ""
echo "To enable dummy mode, set USE_DUMMY_AI=true in .env"
echo "To disable dummy mode, set USE_DUMMY_AI=false in .env"
echo "Then restart: docker compose restart python-agents"
