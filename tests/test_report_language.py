# -*- coding: utf-8 -*-
"""Unit tests for report language helpers."""

import unittest

from src.report_language import (
    get_bias_status_emoji,
    get_localized_stock_name,
    get_sentiment_label,
    get_signal_level,
    localize_bias_status,
    localize_market_term,
    resolve_log_language,
)


class ReportLanguageTestCase(unittest.TestCase):
    def test_get_signal_level_handles_compound_sell_advice(self) -> None:
        signal_text, emoji, signal_tag = get_signal_level("卖出/观望", 60, "zh")

        self.assertEqual(signal_text, "卖出")
        self.assertEqual(emoji, "🔴")
        self.assertEqual(signal_tag, "sell")

    def test_get_signal_level_handles_compound_buy_advice_in_english(self) -> None:
        signal_text, emoji, signal_tag = get_signal_level("Buy / Watch", 40, "en")

        self.assertEqual(signal_text, "Buy")
        self.assertEqual(emoji, "🟢")
        self.assertEqual(signal_tag, "buy")

    def test_get_localized_stock_name_replaces_placeholder_for_english(self) -> None:
        self.assertEqual(
            get_localized_stock_name("股票AAPL", "AAPL", "en"),
            "Apple",
        )

    def test_get_localized_stock_name_prefers_known_english_alias(self) -> None:
        self.assertEqual(
            get_localized_stock_name("腾讯控股", "00700", "en"),
            "Tencent Holdings",
        )

    def test_get_localized_stock_name_prefers_code_alias_for_placeholder(self) -> None:
        self.assertEqual(
            get_localized_stock_name("00700", "00700", "en"),
            "Tencent Holdings",
        )

    def test_get_localized_stock_name_falls_back_to_original_when_alias_missing(self) -> None:
        self.assertEqual(
            get_localized_stock_name("测试公司", "999999", "en"),
            "测试公司",
        )

    def test_get_localized_stock_name_uses_generic_placeholder_when_alias_missing(self) -> None:
        self.assertEqual(
            get_localized_stock_name("股票XYZ1", "XYZ1", "en"),
            "Unnamed Stock",
        )

    def test_get_sentiment_label_preserves_higher_band_thresholds(self) -> None:
        self.assertEqual(get_sentiment_label(80, "en"), "Very Bullish")
        self.assertEqual(get_sentiment_label(60, "en"), "Bullish")
        self.assertEqual(get_sentiment_label(40, "zh"), "中性")
        self.assertEqual(get_sentiment_label(20, "zh"), "悲观")

    def test_bias_status_helpers_support_english_values(self) -> None:
        self.assertEqual(localize_bias_status("Safe", "en"), "Safe")
        self.assertEqual(localize_bias_status("警戒", "en"), "Caution")
        self.assertEqual(get_bias_status_emoji("Safe"), "✅")
        self.assertEqual(get_bias_status_emoji("Caution"), "⚠️")

    def test_localize_market_term_returns_curated_english_alias(self) -> None:
        self.assertEqual(localize_market_term("上证指数", "en"), "Shanghai Composite")
        self.assertEqual(localize_market_term("半导体", "en"), "Semiconductors")

    def test_resolve_log_language_supports_follow_report(self) -> None:
        self.assertEqual(resolve_log_language("en", "zh"), "en")
        self.assertEqual(resolve_log_language("follow_report", "en"), "en")
        self.assertEqual(resolve_log_language("follow_report", "zh"), "zh")


if __name__ == "__main__":
    unittest.main()
