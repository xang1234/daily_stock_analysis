# -*- coding: utf-8 -*-
"""Tests for runtime log localization helpers."""

import unittest

from src.logging_config import translate_runtime_log_text
from src.report_language import contains_cjk_text


class LoggingConfigTestCase(unittest.TestCase):
    def test_translate_runtime_log_text_keeps_chinese_when_requested(self) -> None:
        message = "日志系统初始化完成，日志目录: logs"
        self.assertEqual(
            translate_runtime_log_text(message, log_language="zh", report_language="en"),
            message,
        )

    def test_translate_runtime_log_text_uses_explicit_english(self) -> None:
        message = "日报已保存到: reports/report.md"
        translated = translate_runtime_log_text(
            message,
            log_language="en",
            report_language="zh",
        )
        self.assertIn("Report saved to:", translated)

    def test_translate_runtime_log_text_follows_report_language(self) -> None:
        message = "开始执行大盘复盘分析..."
        translated = translate_runtime_log_text(
            message,
            log_language="follow_report",
            report_language="en",
        )
        self.assertIn("starting market review", translated)

    def test_translate_runtime_log_text_cleans_llm_response_copy(self) -> None:
        message = "[LLM返回] gemini-2.5-pro 响应成功, 耗时 1.23s, 响应长度 123 字符"
        translated = translate_runtime_log_text(
            message,
            log_language="en",
            report_language="zh",
        )
        self.assertIn("[LLM Response]", translated)
        self.assertIn("response length 123 chars", translated)
        self.assertFalse(contains_cjk_text(translated))

    def test_translate_runtime_log_text_cleans_market_review_counts(self) -> None:
        message = "[大盘] 涨:3200 跌:1800 平:120 涨停:88 跌停:6 成交额:10325亿"
        translated = translate_runtime_log_text(
            message,
            log_language="follow_report",
            report_language="en",
        )
        self.assertIn("[Market Review] Up:3200", translated)
        self.assertIn("Turnover:10325 bn CNY", translated)
        self.assertFalse(contains_cjk_text(translated))

    def test_translate_runtime_log_text_cleans_market_review_merge_message(self) -> None:
        message = "合并推送模式：跳过大盘复盘单独推送，将在个股+大盘复盘后统一发送"
        translated = translate_runtime_log_text(
            message,
            log_language="en",
            report_language="zh",
        )
        self.assertIn("skipped standalone market review push", translated)
        self.assertFalse(contains_cjk_text(translated))


if __name__ == "__main__":
    unittest.main()
