"""
User Context Manager Utility
CRUD operations for managing user-specific context files in agent_context/{userId} directories
Designed to be used by agent-level context managers that orchestrate LLM API calls
"""
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from utils.logger import logger


# Base directory for user context storage
USER_CONTEXT_DIR = Path(__file__).parent.parent / "agent_context"


def ensure_user_context_dir(user_id: Optional[str] = None):
    """
    Ensure the agent_context directory exists, optionally for a specific user
    
    Args:
        user_id: Optional user ID to create user-specific directory
    """
    if user_id:
        user_dir = USER_CONTEXT_DIR / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
    else:
        USER_CONTEXT_DIR.mkdir(parents=True, exist_ok=True)


def get_user_context_path(user_id: str, filename: str) -> Path:
    """
    Get the full path for a context file in user's directory
    
    Args:
        user_id: User identifier
        filename: Name of the file
        
    Returns:
        Full path to the file in agent_context/{user_id}/
    """
    return USER_CONTEXT_DIR / user_id / filename


def read_user_context(user_id: str, filename: str) -> Optional[str]:
    """
    Read content from a file in agent_context/{user_id} directory
    
    Args:
        user_id: User identifier
        filename: Name of the file to read
        
    Returns:
        File content as string, or None if file doesn't exist
        
    Example:
        content = read_user_context("user123", "user_preferences.json")
    """
    try:
        ensure_user_context_dir(user_id)
        file_path = get_user_context_path(user_id, filename)
        
        if not file_path.exists():
            logger.warning(f"User context file not found for user {user_id}: {filename}")
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        logger.info(f"Read user context file for user {user_id}: {filename} ({len(content)} bytes)")
        return content
        
    except Exception as e:
        logger.error(f"Error reading user context file {filename} for user {user_id}: {e}")
        return None


def write_user_context(user_id: str, filename: str, content: str) -> bool:
    """
    Write content to a file in agent_context/{user_id} directory
    
    Args:
        user_id: User identifier
        filename: Name of the file to write
        content: Content to write to the file
        
    Returns:
        True if successful, False otherwise
        
    Example:
        write_user_context("user123", "session_data.txt", "User session started")
    """
    try:
        ensure_user_context_dir(user_id)
        file_path = get_user_context_path(user_id, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info(f"Wrote user context file for user {user_id}: {filename} ({len(content)} bytes)")
        return True
        
    except Exception as e:
        logger.error(f"Error writing user context file {filename} for user {user_id}: {e}")
        return False


def update_user_context(user_id: str, filename: str, content: str) -> bool:
    """
    Update (append) content to an existing file in agent_context/{user_id} directory
    
    Args:
        user_id: User identifier
        filename: Name of the file to update
        content: Content to append to the file
        
    Returns:
        True if successful, False otherwise
        
    Example:
        update_user_context("user123", "conversation_log.txt", "\\nNew message")
    """
    try:
        ensure_user_context_dir(user_id)
        file_path = get_user_context_path(user_id, filename)
        
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(content)
            
        logger.info(f"Updated user context file for user {user_id}: {filename} (+{len(content)} bytes)")
        return True
        
    except Exception as e:
        logger.error(f"Error updating user context file {filename} for user {user_id}: {e}")
        return False


def delete_user_context(user_id: str, filename: str) -> bool:
    """
    Delete a file from agent_context/{user_id} directory
    
    Args:
        user_id: User identifier
        filename: Name of the file to delete
        
    Returns:
        True if successful, False otherwise
        
    Example:
        delete_user_context("user123", "temp_session.json")
    """
    try:
        ensure_user_context_dir(user_id)
        file_path = get_user_context_path(user_id, filename)
        
        if not file_path.exists():
            logger.warning(f"User context file not found for deletion for user {user_id}: {filename}")
            return False
            
        file_path.unlink()
        logger.info(f"Deleted user context file for user {user_id}: {filename}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting user context file {filename} for user {user_id}: {e}")
        return False


def list_user_context_files(user_id: str) -> List[str]:
    """
    List all files in the agent_context/{user_id} directory
    
    Args:
        user_id: User identifier
        
    Returns:
        List of filenames
        
    Example:
        files = list_user_context_files("user123")
    """
    try:
        ensure_user_context_dir(user_id)
        user_dir = USER_CONTEXT_DIR / user_id
        files = [f.name for f in user_dir.iterdir() if f.is_file()]
        logger.info(f"Listed {len(files)} user context files for user {user_id}")
        return files
        
    except Exception as e:
        logger.error(f"Error listing user context files for user {user_id}: {e}")
        return []


def read_json_user_context(user_id: str, filename: str) -> Optional[Dict[str, Any]]:
    """
    Read and parse JSON content from agent_context/{user_id} directory
    
    Args:
        user_id: User identifier
        filename: Name of the JSON file to read
        
    Returns:
        Parsed JSON as dict, or None if error
        
    Example:
        data = read_json_user_context("user123", "user_data.json")
    """
    try:
        content = read_user_context(user_id, filename)
        if content is None:
            return None
            
        return json.loads(content)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in user context file {filename} for user {user_id}: {e}")
        return None


def write_json_user_context(user_id: str, filename: str, data: Dict[str, Any]) -> bool:
    """
    Write Python dict as JSON to agent_context/{user_id} directory
    
    Args:
        user_id: User identifier
        filename: Name of the JSON file to write
        data: Dictionary to serialize as JSON
        
    Returns:
        True if successful, False otherwise
        
    Example:
        write_json_user_context("user123", "config.json", {"mode": "active"})
    """
    try:
        content = json.dumps(data, indent=2, ensure_ascii=False)
        return write_user_context(user_id, filename, content)
        
    except Exception as e:
        logger.error(f"Error writing JSON user context file {filename} for user {user_id}: {e}")
        return False


# Convenience functions for common patterns
def clear_all_user_context(user_id: str) -> bool:
    """
    Delete all files in agent_context/{user_id} directory
    
    Args:
        user_id: User identifier
        
    Returns:
        True if successful, False otherwise
    """
    try:
        files = list_user_context_files(user_id)
        for filename in files:
            delete_user_context(user_id, filename)
        logger.info(f"Cleared all user context files for user {user_id} ({len(files)} files)")
        return True
        
    except Exception as e:
        logger.error(f"Error clearing user context files for user {user_id}: {e}")
        return False


def list_all_users() -> List[str]:
    """
    List all user IDs that have context directories
    
    Returns:
        List of user IDs
        
    Example:
        users = list_all_users()
    """
    try:
        ensure_user_context_dir()
        users = [d.name for d in USER_CONTEXT_DIR.iterdir() if d.is_dir()]
        logger.info(f"Found {len(users)} user context directories")
        return users
        
    except Exception as e:
        logger.error(f"Error listing user directories: {e}")
        return []
