#!/usr/bin/env python3
"""
Script to cleanup orphaned agent calls
Run this to fix agent calls stuck in IN_PROGRESS state
"""
import asyncio
import sys
import argparse
from datetime import datetime, timezone
sys.path.insert(0, '/app')

from utils.cleanup_orphaned_agents import orphaned_cleaner
from utils.logger import logger


async def main():
    """Main cleanup function"""
    parser = argparse.ArgumentParser(description='Cleanup orphaned agent calls')
    parser.add_argument(
        '--max-age',
        type=int,
        default=30,
        help='Maximum age in minutes before considering a call orphaned (default: 30)'
    )
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Only show statistics without cleaning up'
    )
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"Orphaned Agent Call Cleanup")
    print(f"{'='*60}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Max Age Threshold: {args.max_age} minutes")
    print(f"Mode: {'Statistics Only' if args.stats_only else 'Cleanup'}")
    print(f"{'='*60}\n")
    
    try:
        if args.stats_only:
            # Get statistics only
            stats = await orphaned_cleaner.get_orphaned_statistics(args.max_age)
            print(f"Orphaned Agent Statistics:")
            print(f"  Total Orphaned: {stats.get('total_orphaned', 0)}")
            print(f"\nBy Agent:")
            for agent_stat in stats.get('by_agent', []):
                print(f"  - {agent_stat['agent']}: {agent_stat['count']} calls")
                print(f"    Average Age: {agent_stat['avg_age_minutes']:.1f} minutes")
                print(f"    Oldest: {agent_stat['oldest']}")
        else:
            # Perform cleanup
            result = await orphaned_cleaner.cleanup_orphaned_calls(args.max_age)
            print(f"Cleanup Results:")
            print(f"  Found: {result['found']} orphaned calls")
            print(f"  Cleaned: {result['cleaned']} calls")
            print(f"  Errors: {result['errors']}")
            
            if result['details']:
                print(f"\nDetails:")
                for detail in result['details']:
                    status = detail.get('status', 'unknown')
                    print(f"  - {detail['id']} ({detail['agent']})")
                    print(f"    Age: {detail.get('age_minutes', 0):.1f} minutes")
                    print(f"    Status: {status}")
                    if status == 'error':
                        print(f"    Error: {detail.get('error', 'unknown')}")
        
        print(f"\n{'='*60}")
        print("Cleanup completed successfully!")
        print(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Failed to run cleanup: {e}")
        print(f"\nERROR: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
