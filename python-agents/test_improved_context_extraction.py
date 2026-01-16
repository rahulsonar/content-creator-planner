"""
Test script to verify improved context extraction from context manager
"""
import asyncio
from models.openai_client import OpenAIClient
from agents.context_manager import ContextManagerAgent
from utils.logger import logger
from utils.user_context_manager import read_user_context, list_user_context_files
import shutil
import os


async def test_improved_extraction():
    """Test that context manager extracts detailed information from user messages"""
    
    # Initialize context manager
    openai_client = OpenAIClient()
    context_manager = ContextManagerAgent(openai_client)
    
    test_user_id = "test_extraction_user_001"
    
    # Clean up any existing test context
    context_dir = f"agent_context/{test_user_id}"
    if os.path.exists(context_dir):
        shutil.rmtree(context_dir)
        logger.info(f"Cleaned up existing context for {test_user_id}")
    
    logger.info("=" * 80)
    logger.info("TESTING IMPROVED CONTEXT EXTRACTION")
    logger.info("=" * 80)
    
    # Test message (from user's example)
    user_message = """I want to start a youtube channel on history of deccan. 
I am doing this first time, so not sure where to start. 
I like to read about history, so I have some knowledge."""
    
    logger.info(f"\n📨 USER MESSAGE:\n{user_message}\n")
    
    # Process message
    logger.info("🤖 Processing message with context manager...")
    response = await context_manager.process_message(
        user_message=user_message,
        user_context={"user_id": test_user_id}
    )
    
    logger.info(f"\n✅ CONTEXT MANAGER RESPONSE:\n{response}\n")
    
    # Check what files were created
    logger.info("=" * 80)
    logger.info("CHECKING SAVED CONTEXT FILES")
    logger.info("=" * 80)
    
    files = list_user_context_files(test_user_id)
    logger.info(f"\n📁 Files created: {files}\n")
    
    # Read and display each file
    for filename in files:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"📄 CONTENT OF {filename}")
        logger.info(f"{'=' * 80}")
        content = read_user_context(test_user_id, filename)
        logger.info(f"\n{content}\n")
    
    # Verify extraction quality
    logger.info("=" * 80)
    logger.info("EXTRACTION QUALITY CHECK")
    logger.info("=" * 80)
    
    expected_extractions = [
        ("YouTube channel", "Should extract platform/goal"),
        ("history of Deccan", "Should extract specific topic/niche"),
        ("first time", "Should extract experience level"),
        ("knowledge", "Should extract background/skills"),
        ("not sure where to start", "Should extract challenge/pain point")
    ]
    
    # Check if key information was extracted
    all_content = ""
    for filename in files:
        all_content += read_user_context(test_user_id, filename) or ""
    
    all_content_lower = all_content.lower()
    
    logger.info("\nChecking for key extractions:")
    found_count = 0
    for keyword, description in expected_extractions:
        found = keyword.lower() in all_content_lower
        status = "✓" if found else "✗"
        logger.info(f"{status} {description}: '{keyword}' {'FOUND' if found else 'MISSING'}")
        if found:
            found_count += 1
    
    logger.info(f"\n📊 Extraction Score: {found_count}/{len(expected_extractions)}")
    
    if found_count >= 4:
        logger.info("✅ EXCELLENT: Context manager extracted most key information")
    elif found_count >= 3:
        logger.info("⚠️  GOOD: Context manager extracted some key information, but could improve")
    else:
        logger.info("❌ POOR: Context manager needs improvement")
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_improved_extraction())
