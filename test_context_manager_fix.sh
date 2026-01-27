#!/bin/bash
# Test the context manager retrieval fix

echo "Testing Context Manager - User Profile Retrieval"
echo "================================================"

# Test retrieving user context for existing user
USER_ID="cmktdyhe6000087jzc59ybmcx"

curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Please provide the user'\''s basic profile (name, role, preferences) and their main goals or content plans.",
    "user_id": "'"$USER_ID"'",
    "session_id": "test-session-fix",
    "conversation_id": "test-conv-fix"
  }' | jq '.'

echo ""
echo "Test complete!"
