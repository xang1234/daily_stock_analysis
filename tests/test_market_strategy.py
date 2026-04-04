# -*- coding: utf-8 -*-
"""Tests for market strategy blueprints."""

import sys
import unittest
from unittest.mock import MagicMock

sys.modules.setdefault("pandas", MagicMock())
sys.modules.setdefault("src.search_service", MagicMock())
sys.modules.setdefault("data_provider.base", MagicMock())

from src.core.market_strategy import get_market_strategy_blueprint
from src.market_analyzer import MarketAnalyzer, MarketOverview


class TestMarketStrategyBlueprint(unittest.TestCase):
    """Validate CN/US strategy blueprint basics."""

    def test_cn_blueprint_contains_action_framework(self):
        blueprint = get_market_strategy_blueprint("cn")
        block = blueprint.to_prompt_block()

        self.assertIn("A股市场三段式复盘策略", block)
        self.assertIn("Action Framework", block)
        self.assertIn("进攻", block)

    def test_cn_blueprint_supports_english_rendering(self):
        blueprint = get_market_strategy_blueprint("cn")
        block = blueprint.to_prompt_block(language="en")

        self.assertIn("China Market Three-Stage Recap", block)
        self.assertIn("Action Framework", block)
        self.assertIn("Offensive", block)

    def test_us_blueprint_contains_regime_strategy(self):
        blueprint = get_market_strategy_blueprint("us")
        block = blueprint.to_prompt_block()

        self.assertIn("US Market Regime Strategy", block)
        self.assertIn("Risk-on", block)
        self.assertIn("Macro & Flows", block)


class TestMarketAnalyzerStrategyPrompt(unittest.TestCase):
    """Validate strategy section is injected into prompt/report."""

    def test_cn_prompt_contains_strategy_plan_section(self):
        analyzer = MarketAnalyzer(region="cn")
        prompt = analyzer._build_review_prompt(MarketOverview(date="2026-02-24"), [])

        self.assertIn("策略计划", prompt)
        self.assertIn("A股市场三段式复盘策略", prompt)

    def test_us_prompt_contains_strategy_plan_section(self):
        analyzer = MarketAnalyzer(region="us", report_language="en")
        prompt = analyzer._build_review_prompt(MarketOverview(date="2026-02-24"), [])

        self.assertIn("Strategy Plan", prompt)
        self.assertIn("US Market Regime Strategy", prompt)

    def test_cn_prompt_uses_english_when_report_language_is_en(self):
        analyzer = MarketAnalyzer(region="cn", report_language="en")
        prompt = analyzer._build_review_prompt(MarketOverview(date="2026-02-24"), [])

        self.assertIn("China A-share Market Review", prompt)
        self.assertIn("Market Summary", prompt)
        self.assertIn("China Market Three-Stage Recap", prompt)
        self.assertNotIn("输出格式模板", prompt)


if __name__ == "__main__":
    unittest.main()
