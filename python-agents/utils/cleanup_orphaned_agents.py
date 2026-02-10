"""
Cleanup Orphaned Agent Calls
Handles agent calls that are stuck in IN_PROGRESS state
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from utils.logger import logger
from storage.database import db_manager


class OrphanedAgentCleaner:
    """Manages cleanup of orphaned agent calls"""
    
    def __init__(self):
        """Initialize cleaner"""
        self.db = db_manager
        
    async def cleanup_orphaned_calls(self, max_age_minutes: int = 30) -> dict:
        """
        Find and cleanup agent calls stuck in IN_PROGRESS state for too long
        
        Args:
            max_age_minutes: Maximum age in minutes before considering a call orphaned
            
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            async with self.db.get_session() as session:
                # Find orphaned calls
                cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
                
                find_query = text("""
                    SELECT 
                        id, "agentName", "userId", "messageId",
                        "startedAt", 
                        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - "startedAt")) / 60 as age_minutes
                    FROM "AgentCallLog"
                    WHERE status = 'IN_PROGRESS'
                      AND "startedAt" < :cutoff_time
                    ORDER BY "startedAt" ASC
                """)
                
                result = await session.execute(
                    find_query,
                    {"cutoff_time": cutoff_time.replace(tzinfo=None)}
                )
                orphaned_calls = result.fetchall()
                
                if not orphaned_calls:
                    logger.info(f"No orphaned agent calls found (older than {max_age_minutes} minutes)")
                    return {
                        "found": 0,
                        "cleaned": 0,
                        "errors": 0,
                        "details": []
                    }
                
                logger.warning(f"Found {len(orphaned_calls)} orphaned agent calls")
                
                # Update orphaned calls to FAILED state
                cleanup_query = text("""
                    UPDATE "AgentCallLog"
                    SET 
                        status = 'FAILED',
                        "completedAt" = CURRENT_TIMESTAMP,
                        "durationMs" = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - "startedAt")) * 1000,
                        error = :error_message,
                        "errorType" = 'orphaned_timeout',
                        metadata = COALESCE(metadata, '{}'::jsonb) || 
                                   jsonb_build_object('cleanup_reason', 'orphaned', 'cleanup_at', CAST(:cleanup_at AS TEXT)),
                        "updatedAt" = CURRENT_TIMESTAMP
                    WHERE id = :log_id
                      AND status = 'IN_PROGRESS'
                """)
                
                cleaned_count = 0
                error_count = 0
                details = []
                
                for call in orphaned_calls:
                    try:
                        await session.execute(
                            cleanup_query,
                            {
                                "log_id": call.id,
                                "error_message": f"Agent call orphaned after {call.age_minutes:.1f} minutes without completion",
                                "cleanup_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
                            }
                        )
                        cleaned_count += 1
                        details.append({
                            "id": call.id,
                            "agent": call.agentName,
                            "user_id": call.userId,
                            "age_minutes": float(call.age_minutes),
                            "started_at": call.startedAt.isoformat() if call.startedAt else None,
                            "status": "cleaned"
                        })
                        logger.info(f"Cleaned orphaned call: {call.id} ({call.agentName}, {call.age_minutes:.1f}min old)")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Failed to cleanup call {call.id}: {e}")
                        details.append({
                            "id": call.id,
                            "agent": call.agentName,
                            "status": "error",
                            "error": str(e)
                        })
                
                await session.commit()
                
                result = {
                    "found": len(orphaned_calls),
                    "cleaned": cleaned_count,
                    "errors": error_count,
                    "details": details
                }
                
                logger.info(f"Cleanup complete: {cleaned_count}/{len(orphaned_calls)} calls cleaned, {error_count} errors")
                return result
                
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned calls: {e}")
            return {
                "found": 0,
                "cleaned": 0,
                "errors": 1,
                "error": str(e)
            }
    
    async def cleanup_orphaned_logs(self, hours_threshold: int = 1) -> int:
        """
        Cleanup orphaned agent logs older than specified hours threshold.
        This is typically used on service startup to clean up logs from previous runs.
        
        Args:
            hours_threshold: Age threshold in hours (default 1 hour)
            
        Returns:
            Number of logs cleaned up
        """
        result = await self.cleanup_orphaned_calls(max_age_minutes=hours_threshold * 60)
        return result.get('cleaned', 0)
    
    async def get_orphaned_statistics(self, max_age_minutes: int = 30) -> dict:
        """
        Get statistics about orphaned agent calls without modifying them
        
        Args:
            max_age_minutes: Threshold for considering calls orphaned
            
        Returns:
            Dictionary with statistics
        """
        try:
            async with self.db.get_session() as session:
                cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
                
                query = text("""
                    SELECT 
                        "agentName",
                        COUNT(*) as count,
                        AVG(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - "startedAt")) / 60) as avg_age_minutes,
                        MIN("startedAt") as oldest_started
                    FROM "AgentCallLog"
                    WHERE status = 'IN_PROGRESS'
                      AND "startedAt" < :cutoff_time
                    GROUP BY "agentName"
                    ORDER BY count DESC
                """)
                
                result = await session.execute(
                    query,
                    {"cutoff_time": cutoff_time.replace(tzinfo=None)}
                )
                stats = result.fetchall()
                
                return {
                    "total_orphaned": sum(s.count for s in stats),
                    "by_agent": [
                        {
                            "agent": s.agentName,
                            "count": s.count,
                            "avg_age_minutes": float(s.avg_age_minutes),
                            "oldest": s.oldest_started.isoformat() if s.oldest_started else None
                        }
                        for s in stats
                    ]
                }
                
        except Exception as e:
            logger.error(f"Failed to get orphaned statistics: {e}")
            return {"error": str(e)}


# Singleton instance
orphaned_cleaner = OrphanedAgentCleaner()
