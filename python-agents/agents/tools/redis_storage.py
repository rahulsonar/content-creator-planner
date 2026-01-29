"""
Redis Storage Tool
Independent tool for storing and retrieving temporary data using Redis
Can be used by any agent that needs temporary storage
"""
from typing import Dict, Any
import json
import traceback
from utils.logger import logger


class RedisStorageTool:
    """
    Tool for managing temporary data storage using Redis.
    Provides a simple key-value storage interface with TTL support.
    """
    
    def __init__(self, redis_client):
        """
        Initialize Redis storage tool.
        
        Args:
            redis_client: Redis client instance for storage operations
        """
        self.redis_client = redis_client
        self.tool_name = "redis_storage"
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Get OpenAI function tool definition.
        
        Returns:
            Tool definition in OpenAI function format
        """
        return {
            "type": "function",
            "function": {
                "name": "redis_storage",
                "description": "Store and retrieve temporary data using Redis key-value storage. Use this to save intermediate planning information, task lists, draft plans, or any other data you need to track during planning. Data can have optional TTL (time-to-live) for automatic expiration.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["set", "get", "delete", "exists"],
                            "description": "Storage operation: 'set' (save data), 'get' (retrieve data), 'delete' (remove data), 'exists' (check if key exists)"
                        },
                        "key": {
                            "type": "string",
                            "description": "Storage key name. Use descriptive keys like 'draft_plan', 'task_list', etc. Will be automatically prefixed with user_id and agent context."
                        },
                        "value":  ["string", "number", "boolean", "object", "array", "null"],
                        "ttl": {
                            "type": "integer",
                            "description": "Time-to-live in seconds (for 'set' operation). Default: 3600 (1 hour). Data will automatically expire after this period."
                        }
                    },
                    "required": ["operation", "key"]
                }
            }
        }
    
    async def execute(
        self, 
        tool_input: Dict[str, Any], 
        user_id: str,
        agent_type: str = "planner"
    ) -> str:
        """
        Execute Redis storage operation.
        
        Args:
            tool_input: Dict with 'operation', 'key', optional 'value' and 'ttl'
            user_id: User identifier for key namespacing
            agent_type: Type of agent using this tool (for key namespacing)
            
        Returns:
            Result message or retrieved data
        """
        try:
            if not self.redis_client:
                return "Error: Redis client not available. Please configure Redis connection."
            
            operation = tool_input.get("operation")
            key = tool_input.get("key", "").strip()
            
            if not key:
                return "Error: 'key' parameter is required."
            
            # Namespace the key with agent_type and user_id to prevent conflicts
            namespaced_key = f"{agent_type}:{user_id}:{key}"
            
            if operation == "set":
                value = tool_input.get("value")
                if value is None:
                    return "Error: 'value' parameter is required for 'set' operation."
                
                ttl = tool_input.get("ttl", 3600)  # Default 1 hour
                
                # Store the value
                success = await self.redis_client.set(namespaced_key, value, ttl=ttl)
                
                if success:
                    logger.info(f"[RedisStorageTool] Stored data: {namespaced_key} (TTL: {ttl}s)")
                    return f"Successfully stored data with key '{key}' (expires in {ttl} seconds)."
                else:
                    return f"Failed to store data with key '{key}'."
            
            elif operation == "get":
                # Retrieve the value
                value = await self.redis_client.get(namespaced_key)
                
                if value is not None:
                    logger.info(f"[RedisStorageTool] Retrieved data: {namespaced_key}")
                    # Return the value as a string (will be JSON if object/array was stored)
                    return f"Retrieved data for key '{key}': {json.dumps(value) if not isinstance(value, str) else value}"
                else:
                    return f"No data found for key '{key}'. It may have expired or never been set."
            
            elif operation == "delete":
                # Delete the key
                success = await self.redis_client.delete(namespaced_key)
                
                if success:
                    logger.info(f"[RedisStorageTool] Deleted data: {namespaced_key}")
                    return f"Successfully deleted data with key '{key}'."
                else:
                    return f"Failed to delete key '{key}' or key does not exist."
            
            elif operation == "exists":
                # Check if key exists
                exists = await self.redis_client.exists(namespaced_key)
                
                logger.info(f"[RedisStorageTool] Checked existence: {namespaced_key} = {exists}")
                return f"Key '{key}' {'exists' if exists else 'does not exist'}."
            
            else:
                return f"Error: Invalid operation '{operation}'. Use 'set', 'get', 'delete', or 'exists'."
        
        except Exception as e:
            logger.error(f"[RedisStorageTool] Error in redis_storage: {e}")
            logger.error(traceback.format_exc())
            return f"Error with Redis storage: {str(e)}"
    
    def is_available(self) -> bool:
        """
        Check if Redis storage is available.
        
        Returns:
            True if Redis client is configured, False otherwise
        """
        return self.redis_client is not None
