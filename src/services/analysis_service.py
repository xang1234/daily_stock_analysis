# -*- coding: utf-8 -*-
"""
===================================
Analysis Service Layer
===================================

Responsibilities:
1. Wrap stock-analysis business logic
2. Call the analyzer and pipeline to execute analysis
3. Persist analysis results to the database
"""

import logging
import uuid
from typing import Optional, Dict, Any

from src.repositories.analysis_repo import AnalysisRepository
from src.report_language import (
    get_sentiment_label,
    get_localized_stock_name,
    localize_operation_advice,
    localize_trend_prediction,
    normalize_report_language,
)

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service object for stock-analysis business logic."""
    
    def __init__(self):
        """Initialize the analysis service."""
        self.repo = AnalysisRepository()
    
    def analyze_stock(
        self,
        stock_code: str,
        report_type: str = "detailed",
        force_refresh: bool = False,
        query_id: Optional[str] = None,
        send_notification: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Run stock analysis.

        Args:
            stock_code: Stock code
            report_type: Report type (simple/detailed)
            force_refresh: Whether to force a refresh
            query_id: Optional query ID
            send_notification: Whether to send notifications; defaults to True for API-triggered runs

        Returns:
            Analysis response dictionary containing:
            - stock_code: Stock code
            - stock_name: Stock name
            - report: Analysis report
        """
        try:
            # Import analysis-related modules lazily
            from src.config import get_config
            from src.core.pipeline import StockAnalysisPipeline
            from src.enums import ReportType
            
            # Generate a query_id if needed
            if query_id is None:
                query_id = uuid.uuid4().hex
            
            # Load config
            config = get_config()
            
            # Create the analysis pipeline
            pipeline = StockAnalysisPipeline(
                config=config,
                query_id=query_id,
                query_source="api"
            )
            
            # Normalize the report type (API: simple/detailed/full/brief -> ReportType)
            rt = ReportType.from_str(report_type)
            
            # Run analysis
            result = pipeline.process_single_stock(
                code=stock_code,
                skip_analysis=False,
                single_stock_notify=send_notification,
                report_type=rt
            )
            
            if result is None:
                logger.warning("Analysis for stock %s returned no result", stock_code)
                return None
            
            # Build the API response
            return self._build_analysis_response(result, query_id, report_type=rt.value)
            
        except Exception as e:
            logger.error("Failed to analyze stock %s: %s", stock_code, e, exc_info=True)
            return None
    
    def _build_analysis_response(
        self, 
        result: Any, 
        query_id: str,
        report_type: str = "detailed",
    ) -> Dict[str, Any]:
        """
        Build the formatted analysis response.

        Args:
            result: AnalysisResult object
            query_id: Query ID
            report_type: Normalized report type

        Returns:
            Formatted response dictionary
        """
        # Extract sniper-point levels
        sniper_points = {}
        if hasattr(result, 'get_sniper_points'):
            sniper_points = result.get_sniper_points() or {}
        
        # Compute localized sentiment labels
        report_language = normalize_report_language(getattr(result, "report_language", "zh"))
        sentiment_label = get_sentiment_label(result.sentiment_score, report_language)
        stock_name = get_localized_stock_name(getattr(result, "name", None), result.code, report_language)
        
        # Build the report structure
        report = {
            "meta": {
                "query_id": query_id,
                "stock_code": result.code,
                "stock_name": stock_name,
                "report_type": report_type,
                "report_language": report_language,
                "current_price": result.current_price,
                "change_pct": result.change_pct,
                "model_used": getattr(result, "model_used", None),
            },
            "summary": {
                "analysis_summary": result.analysis_summary,
                "operation_advice": localize_operation_advice(result.operation_advice, report_language),
                "trend_prediction": localize_trend_prediction(result.trend_prediction, report_language),
                "sentiment_score": result.sentiment_score,
                "sentiment_label": sentiment_label,
            },
            "strategy": {
                "ideal_buy": sniper_points.get("ideal_buy"),
                "secondary_buy": sniper_points.get("secondary_buy"),
                "stop_loss": sniper_points.get("stop_loss"),
                "take_profit": sniper_points.get("take_profit"),
            },
            "details": {
                "news_summary": result.news_summary,
                "technical_analysis": result.technical_analysis,
                "fundamental_analysis": result.fundamental_analysis,
                "risk_warning": result.risk_warning,
            }
        }
        
        return {
            "stock_code": result.code,
            "stock_name": stock_name,
            "report": report,
        }
