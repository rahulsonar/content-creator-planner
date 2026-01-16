#!/bin/bash
# Example: How to run the agent conversation script

echo "=============================================="
echo "Agent Conversation Script - Quick Start Guide"
echo "=============================================="
echo ""
echo "1. The conversation_config.json file is already set up with a sample topic."
echo "2. You can edit it anytime to change the topic, roles, or instructions."
echo ""
echo "Running the conversation..."
echo ""

cd /var/www/html/content-creator-planner/python-agents

# Run inside Docker container
docker exec -it content-planner-python-agents python agent_conversation.py

echo ""
echo "=============================================="
echo "Done! Check the generated .jsonl file for the full conversation."
echo "=============================================="
