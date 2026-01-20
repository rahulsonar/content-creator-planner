#!/usr/bin/env python3
"""
View Agent Call Logs

Usage:
  python view_agent_logs.py                          # Show recent logs
  python view_agent_logs.py --message msg_123abc     # Show logs for specific message
  python view_agent_logs.py --conversation conv_xyz  # Show logs for conversation
  python view_agent_logs.py --agent task_manager     # Show logs for specific agent
  python view_agent_logs.py --failed                 # Show only failed calls
"""

import asyncio
import sys
from datetime import datetime
from typing import Optional
import argparse

# Add parent directory to path to import modules
sys.path.insert(0, '/var/www/html/content-creator-planner/python-agents')

from storage.agent_call_log import agent_call_logger
from utils.logger import logger


def format_duration(ms: Optional[int]) -> str:
    """Format duration in milliseconds to human readable"""
    if ms is None:
        return "N/A"
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms/1000:.2f}s"


def truncate(text: Optional[str], length: int = 50) -> str:
    """Truncate text to specified length"""
    if not text:
        return "N/A"
    if len(text) <= length:
        return text
    return text[:length] + "..."


def format_timestamp(ts) -> str:
    """Format timestamp"""
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    return ts.strftime("%Y-%m-%d %H:%M:%S")


async def view_recent_logs(limit: int = 10, failed_only: bool = False):
    """View recent agent call logs"""
    print("\n" + "="*100)
    print("RECENT AGENT CALL LOGS")
    print("="*100 + "\n")
    
    from storage.database import db_manager
    
    query = """
        SELECT * FROM "AgentCallLog"
        {}
        ORDER BY "startedAt" DESC
        LIMIT $1
    """.format('WHERE status = \'FAILED\'' if failed_only else '')
    
    logs = await db_manager.execute_query(query, [limit])
    
    if not logs:
        print("No logs found.")
        return
    
    for i, log in enumerate(logs, 1):
        print(f"{i}. Log ID: {log['id']}")
        print(f"   Message ID: {log['messageId']}")
        print(f"   Agent: {log['agentName']} ({log.get('agentType', 'N/A')})")
        print(f"   Model: {log['modelName']}")
        print(f"   User: {log['userId']}")
        print(f"   Status: {log['status']}")
        print(f"   Duration: {format_duration(log.get('durationMs'))}")
        print(f"   Started: {format_timestamp(log['startedAt'])}")
        
        if log.get('toolCalls'):
            import json
            tool_calls = json.loads(log['toolCalls']) if isinstance(log['toolCalls'], str) else log['toolCalls']
            tool_names = [tc.get('name', 'unknown') for tc in tool_calls]
            print(f"   Tools: {', '.join(tool_names)}")
        
        if log.get('error'):
            print(f"   Error: {truncate(log['error'], 100)}")
        
        print(f"   Input: {truncate(log.get('inputMessage'), 80)}")
        print(f"   Output: {truncate(log.get('outputMessage'), 80)}")
        print()


async def view_message_journey(message_id: str):
    """View complete journey for a message"""
    print("\n" + "="*100)
    print(f"COMPLETE JOURNEY FOR MESSAGE: {message_id}")
    print("="*100 + "\n")
    
    logs = await agent_call_logger.get_logs_by_message(message_id)
    
    if not logs:
        print(f"No logs found for message_id: {message_id}")
        return
    
    print(f"Total agent calls: {len(logs)}")
    print()
    
    for i, log in enumerate(logs, 1):
        print(f"{i}. {log['agentName'].upper()} - {log['status']}")
        print(f"   Started: {format_timestamp(log['startedAt'])}")
        print(f"   Duration: {format_duration(log.get('durationMs'))}")
        print(f"   Model: {log['modelName']}")
        
        if log.get('toolCalls'):
            import json
            tool_calls = json.loads(log['toolCalls']) if isinstance(log['toolCalls'], str) else log['toolCalls']
            print(f"   Tool Calls:")
            for tc in tool_calls:
                print(f"     - {tc.get('name', 'unknown')}: {truncate(str(tc.get('arguments', {})), 60)}")
        
        if log.get('toolResults'):
            import json
            tool_results = json.loads(log['toolResults']) if isinstance(log['toolResults'], str) else log['toolResults']
            print(f"   Tool Results:")
            for tr in tool_results:
                success = tr.get('success', False)
                status_icon = "✓" if success else "✗"
                print(f"     {status_icon} {truncate(str(tr.get('result', '')), 70)}")
        
        if log.get('error'):
            print(f"   ERROR: {log['error']}")
            if log.get('stackTrace'):
                print(f"   Stack Trace:")
                print("   " + "\n   ".join(log['stackTrace'].split('\n')[:5]))
        
        print(f"   Input: {truncate(log.get('inputMessage'), 80)}")
        print(f"   Output: {truncate(log.get('outputMessage'), 80)}")
        print()


async def view_conversation_logs(conversation_id: str, limit: int = 20):
    """View logs for a conversation"""
    print("\n" + "="*100)
    print(f"LOGS FOR CONVERSATION: {conversation_id}")
    print("="*100 + "\n")
    
    logs = await agent_call_logger.get_logs_by_conversation(conversation_id, limit)
    
    if not logs:
        print(f"No logs found for conversation_id: {conversation_id}")
        return
    
    print(f"Total logs: {len(logs)}")
    print()
    
    # Group by message_id
    from collections import defaultdict
    by_message = defaultdict(list)
    for log in logs:
        by_message[log['messageId']].append(log)
    
    for msg_id, msg_logs in by_message.items():
        print(f"Message: {msg_id}")
        for log in sorted(msg_logs, key=lambda x: x['startedAt']):
            print(f"  → {log['agentName']} ({log['status']}) - {format_duration(log.get('durationMs'))}")
        print()


async def view_agent_logs(agent_name: str, limit: int = 10):
    """View logs for specific agent"""
    print("\n" + "="*100)
    print(f"LOGS FOR AGENT: {agent_name.upper()}")
    print("="*100 + "\n")
    
    logs = await agent_call_logger.get_logs_by_agent(agent_name, limit=limit)
    
    if not logs:
        print(f"No logs found for agent: {agent_name}")
        return
    
    print(f"Total logs: {len(logs)}")
    print()
    
    # Statistics
    total_duration = sum(log.get('durationMs', 0) or 0 for log in logs)
    avg_duration = total_duration / len(logs) if logs else 0
    failed = sum(1 for log in logs if log['status'] == 'FAILED')
    
    print(f"Statistics:")
    print(f"  Total calls: {len(logs)}")
    print(f"  Failed calls: {failed} ({failed/len(logs)*100:.1f}%)")
    print(f"  Avg duration: {format_duration(int(avg_duration))}")
    print()
    
    for i, log in enumerate(logs[:limit], 1):
        print(f"{i}. {log['status']} - {format_timestamp(log['startedAt'])} - {format_duration(log.get('durationMs'))}")
        print(f"   Input: {truncate(log.get('inputMessage'), 80)}")
        if log.get('error'):
            print(f"   Error: {truncate(log['error'], 80)}")
        print()


async def main():
    parser = argparse.ArgumentParser(description='View Agent Call Logs')
    parser.add_argument('--message', help='Show logs for specific message ID')
    parser.add_argument('--conversation', help='Show logs for specific conversation ID')
    parser.add_argument('--agent', help='Show logs for specific agent')
    parser.add_argument('--failed', action='store_true', help='Show only failed calls')
    parser.add_argument('--limit', type=int, default=10, help='Number of logs to show')
    
    args = parser.parse_args()
    
    try:
        if args.message:
            await view_message_journey(args.message)
        elif args.conversation:
            await view_conversation_logs(args.conversation, args.limit)
        elif args.agent:
            await view_agent_logs(args.agent, args.limit)
        else:
            await view_recent_logs(args.limit, args.failed)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
