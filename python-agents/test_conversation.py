#!/usr/bin/env python3
"""
Test script to verify conversation storage
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from storage.conversation import ConversationStorage

async def test_conversation_storage():
    """Test conversation storage operations"""
    print("Starting conversation storage test...")
    
    storage = ConversationStorage()
    
    # Test 1: Create conversation
    print("\n1. Creating conversation...")
    conversation_id = await storage.create_conversation(
        user_id="test-user-123",
        conversation_type="test",
        title="Test Conversation"
    )
    print(f"   ✓ Created conversation: {conversation_id}")
    
    # Test 2: Save messages
    print("\n2. Saving messages...")
    await storage.save_message(
        conversation_id=conversation_id,
        role="user",
        content="Hello, this is a test message"
    )
    print("   ✓ Saved user message")
    
    await storage.save_message(
        conversation_id=conversation_id,
        role="assistant",
        content="Hello! This is an assistant response.",
        model="gpt-4",
        tokens_used=50
    )
    print("   ✓ Saved assistant message")
    
    # Test 3: Retrieve conversation
    print("\n3. Retrieving conversation...")
    conversation = await storage.get_conversation(conversation_id)
    if conversation:
        print(f"   ✓ Retrieved conversation: {conversation['id']}")
        print(f"   - User: {conversation['userId']}")
        print(f"   - Title: {conversation['title']}")
        print(f"   - Messages: {len(conversation.get('messages', []))} messages")
    else:
        print("   ✗ Failed to retrieve conversation")
    
    # Test 4: Get user conversations
    print("\n4. Getting user conversations...")
    conversations = await storage.get_user_conversations(user_id="test-user-123")
    print(f"   ✓ Found {len(conversations)} conversations for user")
    
    print("\n✅ All tests passed!")
    return True

if __name__ == "__main__":
    try:
        asyncio.run(test_conversation_storage())
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
