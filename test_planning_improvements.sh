#!/bin/bash

# Test script to compare agent behavior before/after prompt improvements
# Usage: ./test_planning_agent.sh

echo "🧪 Testing Planning Agent Conversation Flow"
echo "==========================================="
echo ""

CONVERSATION_ID=$(uuidgen)
echo "Test Conversation ID: $CONVERSATION_ID"
echo ""

# Test Case 1: Vague request (should trigger clarifying questions)
echo "📝 Test Case 1: Vague Initial Request"
echo "--------------------------------------"
echo "User Message: 'I want to start a YouTube channel'"
echo ""

curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"conversation_id\": \"$CONVERSATION_ID\",
    \"user_id\": \"test-user\",
    \"message\": \"I want to start a YouTube channel\",
    \"conversation_type\": \"planning\"
  }" | jq -r '.response'

echo ""
echo ""

# Test Case 2: Specific request (should still ask follow-ups)
CONVERSATION_ID_2=$(uuidgen)
echo "📝 Test Case 2: More Specific Request"
echo "--------------------------------------"
echo "User Message: 'I want to create educational videos about physics for high school students'"
echo ""

curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"conversation_id\": \"$CONVERSATION_ID_2\",
    \"user_id\": \"test-user\",
    \"message\": \"I want to create educational videos about physics for high school students\",
    \"conversation_type\": \"planning\"
  }" | jq -r '.response'

echo ""
echo ""

echo "✅ Test complete!"
echo ""
echo "Expected Behaviors:"
echo "1. ✓ Agent asks clarifying questions (experience, timeline, resources)"
echo "2. ✓ Agent does NOT immediately dump a full task list"
echo "3. ✓ Response ends with a follow-up question"
echo "4. ✓ Tone is conversational and collaborative"
echo ""
echo "To view full conversation in database:"
echo "docker exec -it content-planner-db psql -U postgres -d content_planner -c \"SELECT role, LEFT(content, 100) as content_preview FROM \\\"Conversation\\\" WHERE id = '$CONVERSATION_ID'::uuid;\""
