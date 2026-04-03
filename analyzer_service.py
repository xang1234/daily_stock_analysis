# -*- coding: utf-8 -*-
"""
===================================
AI Stock Analysis System - Service Layer
===================================

Responsibilities:
1. Wrap the core analysis logic for multiple callers (CLI, WebUI, Bot)
2. Provide a clean API that does not depend on CLI arguments
3. Support dependency injection for testing and extension
4. Centralize analysis flow and configuration handling
"""

import uuid
from typing import List, Optional

from src.analyzer import AnalysisResult
from src.config import get_config, Config
from src.notification import NotificationService
from src.enums import ReportType
from src.core.pipeline import StockAnalysisPipeline
from src.core.market_review import run_market_review



def analyze_stock(
    stock_code: str,
    config: Config = None,
    full_report: bool = False,
    notifier: Optional[NotificationService] = None
) -> Optional[AnalysisResult]:
    """
    Analyze a single stock.

    Args:
        stock_code: Stock code
        config: Optional config object; defaults to the singleton instance
        full_report: Whether to generate the full report
        notifier: Optional notification service

    Returns:
        Analysis result object
    """
    if config is None:
        config = get_config()
    
    # Create the analysis pipeline
    pipeline = StockAnalysisPipeline(
        config=config,
        query_id=uuid.uuid4().hex,
        query_source="cli"
    )
    
    # Reuse the provided notifier when available
    if notifier:
        pipeline.notifier = notifier
    
    # Choose the report type from full_report
    report_type = ReportType.FULL if full_report else ReportType.SIMPLE
    
    # Run analysis for one stock
    result = pipeline.process_single_stock(
        code=stock_code,
        skip_analysis=False,
        single_stock_notify=notifier is not None,
        report_type=report_type
    )
    
    return result

def analyze_stocks(
    stock_codes: List[str],
    config: Config = None,
    full_report: bool = False,
    notifier: Optional[NotificationService] = None
) -> List[AnalysisResult]:
    """
    Analyze multiple stocks.

    Args:
        stock_codes: List of stock codes
        config: Optional config object; defaults to the singleton instance
        full_report: Whether to generate the full report
        notifier: Optional notification service

    Returns:
        List of analysis results
    """
    if config is None:
        config = get_config()
    
    results = []
    for stock_code in stock_codes:
        result = analyze_stock(stock_code, config, full_report, notifier)
        if result:
            results.append(result)
    
    return results

def perform_market_review(
    config: Config = None,
    notifier: Optional[NotificationService] = None
) -> Optional[str]:
    """
    Run the market review.

    Args:
        config: Optional config object; defaults to the singleton instance
        notifier: Optional notification service

    Returns:
        Market review report content
    """
    if config is None:
        config = get_config()
    
    # Create a pipeline so we can reuse the analyzer and search service
    pipeline = StockAnalysisPipeline(
        config=config,
        query_id=uuid.uuid4().hex,
        query_source="cli"
    )
    
    # Use the provided notifier or fall back to the pipeline notifier
    review_notifier = notifier or pipeline.notifier
    
    # Run the market-review helper
    return run_market_review(
        notifier=review_notifier,
        analyzer=pipeline.analyzer,
        search_service=pipeline.search_service
    )

