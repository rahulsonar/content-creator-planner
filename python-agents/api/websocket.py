"""
WebSocket Endpoint
Handles real-time streaming communication
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
from utils.logger import logger
from agents import OnboardingAgent, PlanningAgent, ModelOrchestrator
from models import OpenAIClient, AnthropicClient
import json


class ConnectionManager:
    """Manages active WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept and store connection"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected: {user_id}")
    
    def disconnect(self, user_id: str):
        """Remove connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected: {user_id}")
    
    async def send_message(self, user_id: str, message: str):
        """Send message to specific user"""
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming responses
    
    Query params expected:
    - token: WebSocket authentication token
    - userId: User identifier
    """
    user_id = None
    
    try:
        # Extract user_id from query params (simplified auth)
        # In production, verify token from Next.js
        user_id = websocket.query_params.get("userId")
        
        if not user_id:
            await websocket.close(code=1008, reason="Missing userId")
            return
        
        # Accept connection
        await manager.connect(websocket, user_id)
        
        # Listen for messages
        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            agent_type = message_data.get("agentType", "chat")
            user_message = message_data.get("message", "")
            
            logger.info(f"WebSocket message from {user_id}: {agent_type}")
            
            # Select model
            model_name = ModelOrchestrator.select_model(agent_type)
            
            # Initialize client
            if "gpt" in model_name:
                client = OpenAIClient(model=model_name)
            else:
                client = AnthropicClient(model=model_name)
            
            # Stream response based on agent type
            if agent_type == "onboarding":
                agent = OnboardingAgent(client)
                async for token in agent.stream_response(user_message):
                    await websocket.send_json({
                        "type": "token",
                        "content": token
                    })
            
            elif agent_type == "planning":
                agent = PlanningAgent(client)
                async for token in agent.stream_response(user_message):
                    await websocket.send_json({
                        "type": "token",
                        "content": token
                    })
            
            else:  # General chat
                messages = [{"role": "user", "content": user_message}]
                async for token in client.stream_completion(messages):
                    await websocket.send_json({
                        "type": "token",
                        "content": token
                    })
            
            # Send completion signal
            await websocket.send_json({
                "type": "complete",
                "model": model_name
            })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {user_id}")
        if user_id:
            manager.disconnect(user_id)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if user_id:
            manager.disconnect(user_id)
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass
