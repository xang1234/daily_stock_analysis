# -*- coding: utf-8 -*-
"""
===================================
Analysis History Repository
===================================

Responsibilities:
1. Wrap database operations for analysis history
2. Provide CRUD-style access helpers
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from src.storage import DatabaseManager, AnalysisHistory

logger = logging.getLogger(__name__)


class AnalysisRepository:
    """Repository wrapper around AnalysisHistory table operations."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the repository.

        Args:
            db_manager: Optional database manager; defaults to the singleton instance
        """
        self.db = db_manager or DatabaseManager.get_instance()
    
    def get_by_query_id(self, query_id: str) -> Optional[AnalysisHistory]:
        """
        Get an analysis record by query_id.

        Args:
            query_id: Query ID

        Returns:
            AnalysisHistory object, or None if not found
        """
        try:
            records = self.db.get_analysis_history(query_id=query_id, limit=1)
            return records[0] if records else None
        except Exception as e:
            logger.error("Failed to query analysis record: %s", e)
            return None
    
    def get_list(
        self,
        code: Optional[str] = None,
        days: int = 30,
        limit: int = 50
    ) -> List[AnalysisHistory]:
        """
        Get a list of analysis records.

        Args:
            code: Optional stock-code filter
            days: Time range in days
            limit: Maximum number of returned records

        Returns:
            List of AnalysisHistory objects
        """
        try:
            return self.db.get_analysis_history(
                code=code,
                days=days,
                limit=limit
            )
        except Exception as e:
            logger.error("Failed to get analysis list: %s", e)
            return []
    
    def save(
        self,
        result: Any,
        query_id: str,
        report_type: str,
        news_content: Optional[str] = None,
        context_snapshot: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Save an analysis result.

        Args:
            result: Analysis result object
            query_id: Query ID
            report_type: Report type
            news_content: News content
            context_snapshot: Context snapshot

        Returns:
            Number of saved records
        """
        try:
            return self.db.save_analysis_history(
                result=result,
                query_id=query_id,
                report_type=report_type,
                news_content=news_content,
                context_snapshot=context_snapshot
            )
        except Exception as e:
            logger.error("Failed to save analysis result: %s", e)
            return 0
    
    def count_by_code(self, code: str, days: int = 30) -> int:
        """
        Count analysis records for a stock.

        Args:
            code: Stock code
            days: Time range in days

        Returns:
            Number of matching records
        """
        try:
            records = self.db.get_analysis_history(code=code, days=days, limit=1000)
            return len(records)
        except Exception as e:
            logger.error("Failed to count analysis records: %s", e)
            return 0
