"""
User Context Storage
Manages user context files and database records
"""
import os
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path
from config.settings import settings
from utils.logger import logger


class UserContextStorage:
    """Manages user context persistence"""
    
    def __init__(self):
        """Initialize user context storage"""
        self.base_path = Path(settings.CONTEXT_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized user context storage at: {self.base_path}")
    
    def get_user_directory(self, user_id: str) -> Path:
        """
        Get user's context directory path
        
        Args:
            user_id: User identifier
            
        Returns:
            Path to user directory
        """
        user_dir = self.base_path / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    async def save_context_markdown(
        self,
        user_id: str,
        context_data: Dict[str, Any]
    ) -> str:
        """
        Save user context as markdown file
        
        Args:
            user_id: User identifier
            context_data: Context data dictionary
            
        Returns:
            File path
        """
        try:
            user_dir = self.get_user_directory(user_id)
            file_path = user_dir / "context.md"
            
            # Format context as markdown
            markdown_content = self._format_context_markdown(context_data)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Saved context markdown for user: {user_id}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error saving context markdown: {e}")
            raise
    
    async def load_context_markdown(
        self,
        user_id: str
    ) -> Optional[str]:
        """
        Load user context markdown
        
        Args:
            user_id: User identifier
            
        Returns:
            Markdown content or None
        """
        try:
            user_dir = self.get_user_directory(user_id)
            file_path = user_dir / "context.md"
            
            if not file_path.exists():
                logger.warning(f"No context file found for user: {user_id}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.debug(f"Loaded context markdown for user: {user_id}")
            return content
            
        except Exception as e:
            logger.error(f"Error loading context markdown: {e}")
            return None
    
    async def save_conversation_backup(
        self,
        user_id: str,
        conversation_type: str,
        messages: list
    ) -> str:
        """
        Save conversation as JSON backup
        
        Args:
            user_id: User identifier
            conversation_type: Type (onboarding, planning)
            messages: List of messages
            
        Returns:
            File path
        """
        try:
            user_dir = self.get_user_directory(user_id)
            file_name = f"{conversation_type}_{int(time.time())}.json"
            file_path = user_dir / file_name
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(messages, f, indent=2)
            
            logger.info(f"Saved conversation backup: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error saving conversation backup: {e}")
            raise
    
    def _format_context_markdown(self, context_data: Dict[str, Any]) -> str:
        """
        Format context data as markdown
        
        Args:
            context_data: Context dictionary
            
        Returns:
            Formatted markdown string
        """
        md = "# Content Creator Profile\n\n"
        
        # Channel information
        md += "## Channel Information\n"
        md += f"- **Channel Name:** {context_data.get('channelName', 'Not specified')}\n"
        md += f"- **Content Type:** {context_data.get('channelType', 'Not specified')}\n"
        md += f"- **Topic/Niche:** {context_data.get('channelTopic', 'Not specified')}\n"
        md += f"- **Channel Size:** {context_data.get('channelSize', 'Not specified')}\n\n"
        
        # Creator info
        md += "## Creator Information\n"
        md += f"- **Age Group:** {context_data.get('ageGroup', 'Not specified')}\n"
        md += f"- **Location:** {context_data.get('location', 'Not specified')}\n"
        md += f"- **Team:** {'Yes' if context_data.get('isTeam') else 'Solo creator'}\n"
        if context_data.get('teamSize'):
            md += f"- **Team Size:** {context_data['teamSize']} people\n"
        md += "\n"
        
        # Content strategy
        md += "## Content Strategy\n"
        md += f"- **Upload Frequency:** {context_data.get('uploadFrequency', 'Not specified')}\n"
        if context_data.get('contentGoals'):
            md += f"\n### Goals\n{context_data['contentGoals']}\n"
        if context_data.get('challenges'):
            md += f"\n### Challenges\n{context_data['challenges']}\n"
        md += "\n"
        
        # Preferences
        if context_data.get('thoughtProcess'):
            md += "## Thought Process & Preferences\n"
            md += f"{context_data['thoughtProcess']}\n\n"
        
        return md
