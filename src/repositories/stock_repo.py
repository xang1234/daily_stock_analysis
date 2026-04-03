# -*- coding: utf-8 -*-
"""
===================================
Stock Data Repository
===================================

Responsibilities:
1. Wrap database operations for stock data
2. Provide query helpers for daily-bar data
"""

import logging
from datetime import date
from typing import Optional, List, Dict, Any

import pandas as pd
from sqlalchemy import and_, desc, select

from src.storage import DatabaseManager, StockDaily

logger = logging.getLogger(__name__)


class StockRepository:
    """Repository wrapper around StockDaily table operations."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the repository.

        Args:
            db_manager: Optional database manager; defaults to the singleton instance
        """
        self.db = db_manager or DatabaseManager.get_instance()
    
    def get_latest(self, code: str, days: int = 2) -> List[StockDaily]:
        """
        Get the most recent N days of data.

        Args:
            code: Stock code
            days: Number of days to fetch

        Returns:
            List of StockDaily objects in descending date order
        """
        try:
            return self.db.get_latest_data(code, days)
        except Exception as e:
            logger.error("Failed to get latest data: %s", e)
            return []
    
    def get_range(
        self,
        code: str,
        start_date: date,
        end_date: date
    ) -> List[StockDaily]:
        """
        Get data within a specific date range.

        Args:
            code: Stock code
            start_date: Start date
            end_date: End date

        Returns:
            List of StockDaily objects
        """
        try:
            return self.db.get_data_range(code, start_date, end_date)
        except Exception as e:
            logger.error("Failed to get data for date range: %s", e)
            return []
    
    def save_dataframe(
        self,
        df: pd.DataFrame,
        code: str,
        data_source: str = "Unknown"
    ) -> int:
        """
        Save a DataFrame to the database.

        Args:
            df: DataFrame containing daily-bar data
            code: Stock code
            data_source: Data source label

        Returns:
            Number of saved records
        """
        try:
            return self.db.save_daily_data(df, code, data_source)
        except Exception as e:
            logger.error("Failed to save daily-bar data: %s", e)
            return 0
    
    def has_today_data(self, code: str, target_date: Optional[date] = None) -> bool:
        """
        Check whether data exists for a given date.

        Args:
            code: Stock code
            target_date: Target date, defaults to today

        Returns:
            Whether data exists
        """
        try:
            return self.db.has_today_data(code, target_date)
        except Exception as e:
            logger.error("Failed to check whether data exists: %s", e)
            return False
    
    def get_analysis_context(
        self, 
        code: str, 
        target_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the analysis context for a stock.

        Args:
            code: Stock code
            target_date: Target date

        Returns:
            Analysis context dictionary
        """
        try:
            return self.db.get_analysis_context(code, target_date)
        except Exception as e:
            logger.error("Failed to get analysis context: %s", e)
            return None

    def get_start_daily(self, *, code: str, analysis_date: date) -> Optional[StockDaily]:
        """Return StockDaily for analysis_date (preferred) or nearest previous date."""
        with self.db.get_session() as session:
            row = session.execute(
                select(StockDaily)
                .where(and_(StockDaily.code == code, StockDaily.date <= analysis_date))
                .order_by(desc(StockDaily.date))
                .limit(1)
            ).scalar_one_or_none()
            return row

    def get_forward_bars(self, *, code: str, analysis_date: date, eval_window_days: int) -> List[StockDaily]:
        """Return forward daily bars after analysis_date, up to eval_window_days."""
        with self.db.get_session() as session:
            rows = session.execute(
                select(StockDaily)
                .where(and_(StockDaily.code == code, StockDaily.date > analysis_date))
                .order_by(StockDaily.date)
                .limit(eval_window_days)
            ).scalars().all()
            return list(rows)
