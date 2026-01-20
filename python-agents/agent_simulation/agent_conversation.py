#!/usr/bin/env python3
"""
DEPRECATED: This script is no longer in use.
It was used for testing agent conversations using Claude/Anthropic models.
Claude/Anthropic support has been removed from the project.

Historical conversation data is preserved in data_archieved/ folder.
"""

# DEPRECATED - DO NOT USE
# This file is kept for historical reference only
raise DeprecationWarning(
    "agent_conversation.py is deprecated. "
    "Claude/Anthropic model support has been removed from the project."
)

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# DEPRECATED: AnthropicClient no longer exists
# from models.anthropic_client import AnthropicClient
from models.openai_client import OpenAIClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AgentConversation:
    """Manages a conversation between Claude (user) and OpenAI (assistant)"""
    
    def __init__(self, config_file: str = "conversation_config.json"):
        """
        Initialize the conversation
        
        Args:
            config_file: Path to the configuration JSON file
        """
        self.config_file = config_file
        self.config = self._load_config()
        
        # Initialize AI clients
        self.claude = AnthropicClient(
            model=self.config.get("claude_model", "claude-sonnet-4-20250514")
        )
        self.openai = OpenAIClient(
            model=self.config.get("openai_model", "gpt-4")
        )
        
        # Conversation history
        self.conversation_history = []
        
    def _load_config(self) -> Dict:
        """Load configuration from JSON file"""
        config_path = Path(self.config_file)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {self.config_file}\n"
                f"Please create it with topic, roles, and instructions."
            )
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Validate required fields
        required_fields = ["topic", "claude_role", "openai_role", "max_turns"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field in config: {field}")
        
        return config
    
    def _build_system_prompt(self, role: str, instructions: str) -> str:
        """Build system prompt for an agent"""
        return f"""{role}

{instructions}

Topic: {self.config['topic']}

Keep your responses conversational and engaging. Build on what the other agent says."""
    
    async def _claude_turn(self, openai_messages: List[Dict]) -> str:
        """
        Claude takes a turn as the user
        
        Args:
            openai_messages: Current conversation from OpenAI's perspective
            
        Returns:
            Claude's response
        """
        # Build Claude's system prompt (persistent across all turns)
        system_prompt = f"""{self.config['claude_role']}

{self.config['claude_instructions']}

Topic: {self.config['topic']}

CRITICAL: You MUST stay in character throughout the entire conversation. Remember your specific role and background at all times."""
        
        # Build Claude's message history
        claude_messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if len(openai_messages) == 0:
            # First turn - Claude initiates
            initial_prompt = f"""Begin the conversation naturally as yourself. Ask your first question about {self.config['topic']}."""
            
            claude_messages.append({
                "role": "user",
                "content": initial_prompt
            })
        else:
            # Subsequent turns - Claude responds to OpenAI
            # Convert OpenAI's messages to Claude's perspective
            # OpenAI format: [user (Claude), assistant (OpenAI), user (Claude), assistant (OpenAI), ...]
            # Claude needs: [user (OpenAI), assistant (Claude), user (OpenAI), assistant (Claude), ...]
            for msg in openai_messages:
                if msg["role"] == "user":
                    # Previous Claude messages become assistant messages for Claude
                    claude_messages.append({
                        "role": "assistant",
                        "content": msg["content"]
                    })
                elif msg["role"] == "assistant":
                    # OpenAI's assistant messages become user messages for Claude
                    claude_messages.append({
                        "role": "user",
                        "content": msg["content"]
                    })
        
        # Generate Claude's response
        response = await self.claude.generate_completion(
            messages=claude_messages
        )
        
        return response
    
    async def _openai_turn(self, messages: List[Dict]) -> str:
        """
        OpenAI takes a turn as the assistant
        
        Args:
            messages: Current conversation history
            
        Returns:
            OpenAI's response
        """
        # Add system message for OpenAI
        system_prompt = self._build_system_prompt(
            self.config['openai_role'],
            self.config.get('openai_instructions', '')
        )
        
        openai_messages = [
            {"role": "system", "content": system_prompt}
        ] + messages
        
        # Generate OpenAI's response
        response = await self.openai.generate_completion(
            messages=openai_messages
        )
        
        return response
    
    async def run_conversation(self):
        """Run the full conversation between agents"""
        print("=" * 80)
        print(f"Starting Conversation: {self.config['topic']}")
        print("=" * 80)
        print(f"Claude Role: {self.config['claude_role']}")
        print(f"OpenAI Role: {self.config['openai_role']}")
        print(f"Max Turns: {self.config['max_turns']}")
        print("=" * 80)
        print()
        
        # OpenAI's message history (from assistant's perspective)
        openai_messages = []
        
        max_turns = self.config['max_turns']
        
        for turn in range(max_turns):
            print(f"\n--- Turn {turn + 1}/{max_turns} ---\n")
            
            # Claude's turn (user)
            print("🤖 Claude (User):")
            claude_response = await self._claude_turn(openai_messages)
            print(claude_response)
            print()
            
            # Add to conversation history
            openai_messages.append({
                "role": "user",
                "content": claude_response
            })
            
            self.conversation_history.append({
                "turn": turn + 1,
                "agent": "claude",
                "role": "user",
                "content": claude_response,
                "timestamp": datetime.now().isoformat()
            })
            
            # OpenAI's turn (assistant)
            print("🔮 OpenAI (Assistant):")
            openai_response = await self._openai_turn(openai_messages)
            print(openai_response)
            print()
            
            # Add to conversation history
            openai_messages.append({
                "role": "assistant",
                "content": openai_response
            })
            
            self.conversation_history.append({
                "turn": turn + 1,
                "agent": "openai",
                "role": "assistant",
                "content": openai_response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Small delay between turns
            await asyncio.sleep(1)
        
        print("\n" + "=" * 80)
        print("Conversation Complete!")
        print("=" * 80)
    
    def export_to_jsonl(self, output_file: str = None):
        """
        Export conversation to JSONL file
        
        Args:
            output_file: Output file path (auto-generated if None)
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"agent_simulation/data/conversation_{timestamp}.jsonl"
        
        output_path = Path(output_file)
        
        # Add metadata as first line
        metadata = {
            "type": "metadata",
            "topic": self.config['topic'],
            "claude_role": self.config['claude_role'],
            "openai_role": self.config['openai_role'],
            "claude_model": self.config.get('claude_model', 'claude-sonnet-4-20250514'),
            "openai_model": self.config.get('openai_model', 'gpt-4'),
            "max_turns": self.config['max_turns'],
            "total_messages": len(self.conversation_history),
            "export_time": datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            # Write metadata
            f.write(json.dumps(metadata) + '\n')
            
            # Write each conversation turn
            for entry in self.conversation_history:
                f.write(json.dumps(entry) + '\n')
        
        print(f"\n✅ Conversation exported to: {output_path}")
        print(f"   Total messages: {len(self.conversation_history)}")
        return str(output_path)
    
    def export_to_markdown(self, output_file: str = None):
        """
        Export conversation to Markdown file
        
        Args:
            output_file: Output file path (auto-generated if None)
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"agent_simulation/data/conversation_{timestamp}.md"
        
        output_path = Path(output_file)
        
        with open(output_path, 'w') as f:
            # Write header
            f.write(f"# AI Agent Conversation\n\n")
            f.write(f"**Topic:** {self.config['topic']}\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}\n\n")
            
            # Write metadata section
            f.write("## Configuration\n\n")
            f.write(f"- **Claude Role:** {self.config['claude_role']}\n")
            f.write(f"- **OpenAI Role:** {self.config['openai_role']}\n")
            f.write(f"- **Claude Model:** {self.config.get('claude_model', 'claude-sonnet-4-20250514')}\n")
            f.write(f"- **OpenAI Model:** {self.config.get('openai_model', 'gpt-4')}\n")
            f.write(f"- **Max Turns:** {self.config['max_turns']}\n")
            f.write(f"- **Total Messages:** {len(self.conversation_history)}\n\n")
            
            # Write instructions if available
            if 'claude_instructions' in self.config:
                f.write("### Claude Instructions\n\n")
                f.write(f"{self.config['claude_instructions']}\n\n")
            
            if 'openai_instructions' in self.config:
                f.write("### OpenAI Instructions\n\n")
                f.write(f"{self.config['openai_instructions']}\n\n")
            
            # Write conversation section
            f.write("---\n\n## Conversation\n\n")
            
            # Write each turn
            for entry in self.conversation_history:
                turn_num = entry['turn']
                agent = entry['agent']
                content = entry['content']
                timestamp = entry.get('timestamp', '')
                
                # Format agent name with emoji
                agent_emoji = "🧠" if agent == "claude" else "🔮"
                agent_name = "Claude (User)" if agent == "claude" else "OpenAI (Assistant)"
                
                # Write turn header
                f.write(f"### Turn {turn_num}: {agent_emoji} {agent_name}\n\n")
                if timestamp:
                    parsed_time = datetime.fromisoformat(timestamp)
                    f.write(f"*{parsed_time.strftime('%H:%M:%S')}*\n\n")
                
                # Write message content
                f.write(f"{content}\n\n")
                f.write("---\n\n")
            
            # Write footer
            f.write("## Summary\n\n")
            f.write(f"This conversation consisted of {len(self.conversation_history)} messages ")
            f.write(f"across {self.config['max_turns']} turns.\n\n")
            f.write(f"*Exported on {datetime.now().isoformat()}*\n")
        
        print(f"✅ Conversation exported to Markdown: {output_path}")
        return str(output_path)


async def main():
    """Main entry point"""
    # Check for custom config file argument
    config_file = "agent_simulation/conversation_config.json"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    try:
        # Create and run conversation
        conversation = AgentConversation(config_file)
        await conversation.run_conversation()
        
        # Export to both JSONL and Markdown
        jsonl_file = conversation.export_to_jsonl()
        md_file = conversation.export_to_markdown()
        
        print(f"\n✨ All done! Conversation saved in two formats:")
        print(f"   📄 JSONL: {jsonl_file}")
        print(f"   📝 Markdown: {md_file}")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nCreate a conversation_config.json file with the following structure:")
        print(json.dumps({
            "topic": "The future of AI in creative industries",
            "claude_role": "Creative Director seeking AI solutions",
            "openai_role": "AI Technology Consultant",
            "claude_instructions": "You're a creative director curious about AI tools. Ask thoughtful questions.",
            "openai_instructions": "You're an AI expert helping creatives adopt technology. Be helpful and practical.",
            "max_turns": 5,
            "temperature": 0.7,
            "max_tokens": 800,
            "claude_model": "claude-sonnet-4-20250514",
            "openai_model": "gpt-4"
        }, indent=2))
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
