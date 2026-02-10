"""
User Context Manager Utility
Bare file operations for user-specific context files in agent_context/{userId} directories
"""
from pathlib import Path
from typing import Optional, List, Union


# Base directory for user context storage
USER_CONTEXT_DIR = Path(__file__).parent.parent / "agent_context"


def ensure_user_context_dir(user_id: Optional[Union[str, int]] = None):
    """
    Ensure the agent_context directory exists, optionally for a specific user
    
    Args:
        user_id: Optional user ID to create user-specific directory (int or str)
    """
    if user_id:
        (USER_CONTEXT_DIR / str(user_id)).mkdir(parents=True, exist_ok=True)
    else:
        USER_CONTEXT_DIR.mkdir(parents=True, exist_ok=True)


def get_user_context_path(user_id: Union[str, int], filename: str) -> Path:
    """
    Get the full path for a context file in user's directory
    
    Args:
        user_id: User identifier (int or str)
        filename: Name of the file
        
    Returns:
        Full path to the file in agent_context/{user_id}/
    """
    return USER_CONTEXT_DIR / str(user_id) / filename


def read_user_context(user_id: Union[str, int], filename: str) -> Optional[str]:
    """
    Read content from a file in agent_context/{user_id} directory
    
    Args:
        user_id: User identifier (int or str)
        filename: Name of the file to read
        
    Returns:
        File content as string, or None if file doesn't exist
        
    Example:
        content = read_user_context("user123", "user_preferences.json")
    """
    ensure_user_context_dir(user_id)
    file_path = get_user_context_path(user_id, filename)

    if not file_path.exists():
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def write_user_context(user_id: Union[str, int], filename: str, content: str) -> bool:
    """
    Write content to a file in agent_context/{user_id} directory
    
    Args:
        user_id: User identifier (int or str)
        filename: Name of the file to write
        content: Content to write to the file
        
    Returns:
        True if successful, False otherwise
        
    Example:
        write_user_context("user123", "session_data.txt", "User session started")
    """
    ensure_user_context_dir(user_id)
    file_path = get_user_context_path(user_id, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True


def update_user_context(user_id: Union[str, int], filename: str, content: str) -> bool:
    """
    Update (append) content to an existing file in agent_context/{user_id} directory
    
    Args:
        user_id: User identifier (int or str)
        filename: Name of the file to update
        content: Content to append to the file
        
    Returns:
        True if successful, False otherwise
        
    Example:
        update_user_context("user123", "conversation_log.txt", "\\nNew message")
    """
    ensure_user_context_dir(user_id)
    file_path = get_user_context_path(user_id, filename)

    with open(file_path, "a", encoding="utf-8") as f:
        f.write(content)

    return True


def delete_user_context(user_id: Union[str, int], filename: str) -> bool:
    """
    Delete a file from agent_context/{user_id} directory
    
    Args:
        user_id: User identifier (int or str)
        filename: Name of the file to delete
        
    Returns:
        True if successful, False otherwise
        
    Example:
        delete_user_context("user123", "temp_session.json")
    """
    ensure_user_context_dir(user_id)
    file_path = get_user_context_path(user_id, filename)

    if not file_path.exists():
        return False

    file_path.unlink()
    return True


def list_user_context_files(user_id: Union[str, int]) -> List[str]:
    """
    List all files in the agent_context/{user_id} directory
    
    Args:
        user_id: User identifier (int or str)
        
    Returns:
        List of filenames
        
    Example:
        files = list_user_context_files("user123")
    """
    ensure_user_context_dir(user_id)
    user_dir = USER_CONTEXT_DIR / str(user_id)
    return [f.name for f in user_dir.iterdir() if f.is_file()]
