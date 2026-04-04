# -*- coding: utf-8 -*-
"""
===================================
Report Engine - Report renderer tests
===================================

Tests for Jinja2 report rendering and fallback behavior.
"""

import sys
import unittest
from importlib.util import find_spec
from types import SimpleNamespace
from unittest.mock import MagicMock

from tests.module_stubs import temporary_sys_modules

_REPORT_RENDERER_IMPORT_STUBS = {
    "json_repair": SimpleNamespace(repair_json=lambda value: value),
    "src.storage": SimpleNamespace(persist_llm_usage=MagicMock()),
}
if "litellm" not in sys.modules:
    _REPORT_RENDERER_IMPORT_STUBS["litellm"] = MagicMock()

with temporary_sys_modules(
    _REPORT_RENDERER_IMPORT_STUBS,
    restore_modules=("src.analyzer", "src.services.report_renderer"),
):
    from src.analyzer import AnalysisResult
    from src.services.report_renderer import render


def _make_result(
    code: str = "600519",
    name: str = "贵州茅台",
    sentiment_score: int = 72,
    operation_advice: str = "持有",
    analysis_summary: str = "稳健",
    decision_type: str = "hold",
    dashboard: dict = None,
    report_language: str = "zh",
) -> AnalysisResult:
    if dashboard is None:
        dashboard = {
            "core_conclusion": {"one_sentence": "持有观望"},
            "intelligence": {"risk_alerts": []},
            "battle_plan": {"sniper_points": {"stop_loss": "110"}},
        }
    return AnalysisResult(
        code=code,
        name=name,
        trend_prediction="看多",
        sentiment_score=sentiment_score,
        operation_advice=operation_advice,
        analysis_summary=analysis_summary,
        decision_type=decision_type,
        dashboard=dashboard,
        report_language=report_language,
    )


class TestReportRenderer(unittest.TestCase):
    """Report renderer tests."""

    @unittest.skipUnless(find_spec("jinja2") is not None, "jinja2 not installed")
    def test_render_markdown_summary_only(self) -> None:
        """Markdown platform renders with summary_only."""
        r = _make_result()
        out = render("markdown", [r], summary_only=True)
        self.assertIsNotNone(out)
        self.assertIn("决策仪表盘", out)
        self.assertIn("贵州茅台", out)
        self.assertIn("持有", out)

    @unittest.skipUnless(find_spec("jinja2") is not None, "jinja2 not installed")
    def test_render_markdown_full(self) -> None:
        """Markdown platform renders full report."""
        r = _make_result()
        out = render("markdown", [r], summary_only=False)
        self.assertIsNotNone(out)
        self.assertIn("核心结论", out)
        self.assertIn("作战计划", out)

    @unittest.skipUnless(find_spec("jinja2") is not None, "jinja2 not installed")
    def test_render_wechat(self) -> None:
        """Wechat platform renders."""
        r = _make_result()
        out = render("wechat", [r])
        self.assertIsNotNone(out)
        self.assertIn("贵州茅台", out)

    @unittest.skipUnless(find_spec("jinja2") is not None, "jinja2 not installed")
    def test_render_brief(self) -> None:
        """Brief platform renders 3-5 sentence summary."""
        r = _make_result()
        out = render("brief", [r])
        self.assertIsNotNone(out)
        self.assertIn("决策简报", out)
        self.assertIn("贵州茅台", out)

    @unittest.skipUnless(find_spec("jinja2") is not None, "jinja2 not installed")
    def test_render_markdown_in_english(self) -> None:
        """Markdown renderer switches headings and summary labels for English reports."""
        r = _make_result(
            name="Kweichow Moutai",
            operation_advice="Buy",
            analysis_summary="Momentum remains constructive.",
            report_language="en",
        )
        out = render("markdown", [r], summary_only=True)
        self.assertIsNotNone(out)
        self.assertIn("Decision Dashboard", out)
        self.assertIn("Summary", out)
        self.assertIn("Buy", out)

    @unittest.skipUnless(find_spec("jinja2") is not None, "jinja2 not installed")
    def test_render_markdown_market_snapshot_uses_template_context(self) -> None:
        """Market snapshot macro should render localized labels with template context."""
        r = _make_result(
            code="AAPL",
            name="Apple",
            operation_advice="Buy",
            report_language="en",
        )
        r.market_snapshot = {
            "close": "180.10",
            "prev_close": "178.25",
            "open": "179.00",
            "high": "181.20",
            "low": "177.80",
            "pct_chg": "+1.04%",
            "change_amount": "1.85",
            "amplitude": "1.91%",
            "volume": "1200000",
            "amount": "215000000",
            "price": "180.35",
            "volume_ratio": "1.2",
            "turnover_rate": "0.8%",
            "source": "polygon",
        }

        out = render("markdown", [r], summary_only=False)

        self.assertIsNotNone(out)
        self.assertIn("Market Snapshot", out)
        self.assertIn("Volume Ratio", out)

    @unittest.skipUnless(find_spec("jinja2") is not None, "jinja2 not installed")
    def test_render_markdown_fallback_labels_are_localized_in_english(self) -> None:
        r = _make_result(
            code="AAPL",
            name="Apple",
            operation_advice="Buy",
            analysis_summary="Constructive setup.",
            dashboard={},
            report_language="en",
        )
        r.dashboard = None
        r.buy_reason = "Trend and catalysts are aligned."
        r.risk_warning = "Watch for valuation compression."

        out = render("markdown", [r], summary_only=False)

        self.assertIsNotNone(out)
        self.assertIn("Rationale", out)
        self.assertIn("Risk Warning", out)
        self.assertNotIn("操作理由", out)
        self.assertNotIn("风险提示", out)

    def test_render_unknown_platform_returns_none(self) -> None:
        """Unknown platform returns None (caller fallback)."""
        r = _make_result()
        out = render("unknown_platform", [r])
        self.assertIsNone(out)

    @unittest.skipUnless(find_spec("jinja2") is not None, "jinja2 not installed")
    def test_render_empty_results_returns_content(self) -> None:
        """Empty results still produces header."""
        out = render("markdown", [], summary_only=True)
        self.assertIsNotNone(out)
        self.assertIn("0", out)
