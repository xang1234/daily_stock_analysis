# -*- coding: utf-8 -*-
"""
===================================
日志配置模块 - 统一的日志系统初始化
===================================

职责：
1. 提供统一的日志格式和配置常量
2. 支持控制台 + 文件（常规/调试）三层日志输出
3. 自动降低第三方库日志级别
"""

import logging
import re
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional

from src.report_language import resolve_log_language


LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(pathname)s:%(lineno)d | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_STATIC_LOG_REPLACEMENTS = [
    ("日志系统初始化完成，日志目录:", "Logging initialized. Log directory:"),
    ("常规日志:", "Main log:"),
    ("调试日志:", "Debug log:"),
    ("调度器初始化完成，最大并发数:", "Scheduler initialized. Max workers:"),
    ("已启用技术分析引擎（均线/趋势/量价指标）", "Technical analysis engine enabled (moving averages/trend/price-volume indicators)"),
    ("实时行情已启用 (优先级:", "Realtime quotes enabled (priority:"),
    ("实时行情已禁用，将使用历史收盘价", "Realtime quotes disabled; using historical close prices"),
    ("筹码分布分析已启用", "Chip distribution analysis enabled"),
    ("筹码分布分析已禁用", "Chip distribution analysis disabled"),
    ("搜索服务已启用", "Search service enabled"),
    ("搜索服务未启用（未配置搜索能力）", "Search service unavailable (no search capability configured)"),
    ("开始从数据源获取数据...", "start fetching market data..."),
    ("数据保存成功（来源:", "data saved successfully (source:"),
    ("，新增 ", ", added "),
    (" 条）", " rows)"),
    ("所有实时行情数据源均不可用，已降级为历史收盘价继续分析", "all realtime quote sources failed; downgraded to historical-close analysis"),
    ("实时行情已禁用，使用历史收盘价继续分析", "realtime quotes disabled; continuing with historical-close analysis"),
    ("实时行情链路异常，已降级为历史收盘价继续分析:", "realtime quote path failed; downgraded to historical-close analysis:"),
    ("获取筹码分布失败:", "failed to fetch chip distribution:"),
    ("开始多维度情报搜索...", "starting multi-source intelligence search..."),
    ("情报搜索完成: 共 ", "intelligence search completed: total "),
    (" 条结果", " results"),
    ("搜索服务不可用，跳过情报搜索", "search service unavailable; skipping intelligence search"),
    ("无法获取历史行情数据，将仅基于新闻和实时行情分析", "historical price data unavailable; analysis will rely on news and realtime quotes"),
    ("保存分析历史失败:", "failed to save analysis history:"),
    ("分析失败:", "analysis failed:"),
    ("===== 开始分析 ", "===== Starting analysis for "),
    (" 只股票 =====", " stocks ====="),
    ("股票列表:", "Stock list:"),
    ("并发数:", "Max workers:"),
    ("模式: 仅获取数据", "Mode: data fetch only"),
    ("模式: 完整分析", "Mode: full analysis"),
    ("已启用批量预取架构：一次拉取全市场数据，", "Batch prefetch enabled: pulled full-market data once, shared by "),
    (" 只股票共享缓存", " stocks through shared cache"),
    ("===== 分析完成 =====", "===== Analysis completed ====="),
    ("成功:", "Success:"),
    ("失败:", "Failed:"),
    ("耗时:", "Elapsed:"),
    ("单股推送模式：跳过汇总推送，仅保存报告到本地", "Single-stock notification mode: skipped aggregate push and only saved local reports"),
    ("合并推送模式：跳过本次推送，将在个股+大盘复盘后统一发送", "Merged notification mode: skipped this push and will send stock + market review together"),
    ("合并推送模式：跳过大盘复盘单独推送，将在个股+大盘复盘后统一发送", "Merged notification mode: skipped standalone market review push and will send stock + market review together"),
    ("使用完整报告格式", "using full report format"),
    ("使用简洁报告格式", "using brief report format"),
    ("使用精简报告格式", "using simple report format"),
    ("单股推送成功", "single-stock notification sent successfully"),
    ("单股推送失败", "single-stock notification failed"),
    ("单股推送异常:", "single-stock notification error:"),
    ("决策仪表盘日报已保存:", "Decision dashboard report saved:"),
    ("保存本地报告失败:", "failed to save local report:"),
    ("生成决策仪表盘日报...", "generating decision dashboard report..."),
    ("决策仪表盘推送成功", "decision dashboard sent successfully"),
    ("决策仪表盘推送失败", "decision dashboard send failed"),
    ("通知渠道未配置，跳过推送", "no notification channel configured; skipping push"),
    ("发送通知失败:", "failed to send notification:"),
    ("开始执行大盘复盘分析...", "starting market review..."),
    ("生成 A 股大盘复盘报告...", "generating China market review..."),
    ("生成美股大盘复盘报告...", "generating US market review..."),
    ("大盘复盘报告已保存:", "market review saved:"),
    ("大盘复盘推送成功", "market review sent successfully"),
    ("大盘复盘推送失败", "market review send failed"),
    ("已跳过推送通知 (--no-notify)", "notification skipped (--no-notify)"),
    ("大盘复盘分析失败:", "market review failed:"),
    ("========== 开始大盘复盘分析 ==========", "========== Starting market review analysis =========="),
    ("========== 大盘复盘分析完成 ==========", "========== Market review analysis completed =========="),
    ("[大盘] 获取主要指数实时行情...", "[Market Review] Fetching main indices..."),
    ("[大盘] 所有行情数据源失败，将依赖新闻搜索进行分析", "[Market Review] All quote sources failed; falling back to news-led analysis"),
    ("[大盘] 获取到 ", "[Market Review] Retrieved "),
    (" 个指数行情", " index quotes"),
    ("[大盘] 获取指数行情失败:", "[Market Review] Failed to fetch index quotes:"),
    ("[大盘] 获取市场涨跌统计...", "[Market Review] Fetching market breadth statistics..."),
    ("[大盘] 涨:", "[Market Review] Up:"),
    (" 跌:", " Down:"),
    (" 平:", " Flat:"),
    (" 涨停:", " Limit up:"),
    (" 跌停:", " Limit down:"),
    (" 成交额:", " Turnover:"),
    ("[大盘] 获取涨跌统计失败:", "[Market Review] Failed to fetch breadth statistics:"),
    ("[大盘] 获取板块涨跌榜...", "[Market Review] Fetching sector rankings..."),
    ("[大盘] 领涨板块:", "[Market Review] Leading sectors:"),
    ("[大盘] 领跌板块:", "[Market Review] Lagging sectors:"),
    ("[大盘] 获取板块涨跌榜失败:", "[Market Review] Failed to fetch sector rankings:"),
    ("[大盘] 搜索服务未配置，跳过新闻搜索", "[Market Review] Search service not configured; skipping news search"),
    ("[大盘] 开始搜索市场新闻...", "[Market Review] Searching market news..."),
    ("[大盘] 搜索 '", "[Market Review] Query '"),
    ("' 获取 ", "' returned "),
    ("[大盘] 共获取 ", "[Market Review] Total market news items: "),
    (" 条市场新闻", " market news items"),
    ("[大盘] 搜索市场新闻失败:", "[Market Review] Market news search failed:"),
    ("[大盘] AI分析器未配置或不可用，使用模板生成报告", "[Market Review] AI analyzer unavailable; using template report"),
    ("[大盘] 调用大模型生成复盘报告...", "[Market Review] Calling LLM for market review..."),
    ("[大盘] 复盘报告生成成功，长度:", "[Market Review] Market review generated successfully, length:"),
    ("[大盘] 大模型返回为空，使用模板报告", "[Market Review] LLM returned empty content; using template report"),
    ("AI 分析 ", "AI Analysis "),
    ("========== AI 分析 ", "========== AI Analysis "),
    ("[LLM配置] 模型:", "[LLM Config] Model:"),
    ("[LLM配置] Prompt 长度:", "[LLM Config] Prompt length:"),
    ("[LLM配置] 是否包含新闻: 是", "[LLM Config] Includes news: yes"),
    ("[LLM配置] 是否包含新闻: 否", "[LLM Config] Includes news: no"),
    ("[LLM Prompt 预览]", "[LLM Prompt Preview]"),
    ("[LLM调用] 开始调用 ", "[LLM Call] Calling "),
    ("[LLM返回] ", "[LLM Response] "),
    (" 响应成功, 耗时 ", " succeeded, elapsed "),
    ("响应长度 ", "response length "),
    ("[LLM返回 预览]", "[LLM Response Preview]"),
    ("[LLM完整性] 必填字段缺失 ", "[LLM Integrity] Missing mandatory fields "),
    ("，第 ", ", retry "),
    (" 次补全重试", ""),
    ("已占位补全，不阻塞流程", "filled with placeholders; continuing"),
    ("[LLM解析] ", "[LLM Parse] "),
    (" 分析完成: ", " completed: "),
    ("评分 ", "score "),
    ("日报已保存到:", "Report saved to:"),
    ("通知发送完成：成功 ", "Notification dispatch completed: success "),
    (" 个，失败 ", ", failed "),
    (" 个", ""),
]

_REGEX_LOG_REPLACEMENTS = [
    (
        re.compile(r"^(?P<prefix>.*)\[(?P<code>[^\]]+)\] 数据获取失败: (?P<error>.+)$"),
        lambda m: f"{m.group('prefix')}[{m.group('code')}] data fetch failed: {m.group('error')}",
    ),
    (
        re.compile(r"(?P<count>\d+)\s*字符"),
        lambda m: f"{m.group('count')} chars",
    ),
    (
        re.compile(r"^(?P<prefix>.*)AI Analysis (?P<target>.+) 失败: (?P<error>.+)$"),
        lambda m: f"{m.group('prefix')}AI Analysis {m.group('target')} failed: {m.group('error')}",
    ),
    (
        re.compile(r"^(?P<prefix>.*Turnover:)(?P<amount>-?\d+(?:\.\d+)?)亿$"),
        lambda m: f"{m.group('prefix')}{m.group('amount')} bn CNY",
    ),
]


def translate_runtime_log_text(
    message: str,
    *,
    log_language: Optional[str] = None,
    report_language: Optional[str] = None,
) -> str:
    """Translate common runtime log copy into English when requested."""
    effective_language = resolve_log_language(log_language, report_language)
    if effective_language != "en" or not message:
        return message

    translated = str(message)
    for source, target in _STATIC_LOG_REPLACEMENTS:
        translated = translated.replace(source, target)
    for pattern, replacer in _REGEX_LOG_REPLACEMENTS:
        translated = pattern.sub(replacer, translated)
    return translated


class RelativePathFormatter(logging.Formatter):
    """自定义 Formatter，输出相对路径而非绝对路径"""

    def __init__(
        self,
        fmt=None,
        datefmt=None,
        relative_to=None,
        *,
        log_language: Optional[str] = None,
        report_language: Optional[str] = None,
    ):
        super().__init__(fmt, datefmt)
        self.relative_to = Path(relative_to) if relative_to else Path.cwd()
        self.log_language = log_language
        self.report_language = report_language

    def format(self, record):
        # 将绝对路径转为相对路径
        try:
            record.pathname = str(Path(record.pathname).relative_to(self.relative_to))
        except ValueError:
            # 如果无法转换为相对路径，保持原样
            pass
        formatted = super().format(record)
        return translate_runtime_log_text(
            formatted,
            log_language=self.log_language,
            report_language=self.report_language,
        )



# 默认需要降低日志级别的第三方库
DEFAULT_QUIET_LOGGERS = [
    'urllib3',
    'sqlalchemy',
    'google',
    'httpx',
]


def setup_logging(
    log_prefix: str = "app",
    log_dir: str = "./logs",
    console_level: Optional[int] = None,
    debug: bool = False,
    extra_quiet_loggers: Optional[List[str]] = None,
    log_language: Optional[str] = None,
    report_language: Optional[str] = None,
) -> None:
    """
    统一的日志系统初始化

    配置三层日志输出：
    1. 控制台：根据 debug 参数或 console_level 设置级别
    2. 常规日志文件：INFO 级别，10MB 轮转，保留 5 个备份
    3. 调试日志文件：DEBUG 级别，50MB 轮转，保留 3 个备份

    Args:
        log_prefix: 日志文件名前缀（如 "api_server" -> api_server_20240101.log）
        log_dir: 日志文件目录，默认 ./logs
        console_level: 控制台日志级别（可选，优先于 debug 参数）
        debug: 是否启用调试模式（控制台输出 DEBUG 级别）
        extra_quiet_loggers: 额外需要降低日志级别的第三方库列表
        log_language: 运行日志语言（zh / en / follow_report）
        report_language: 报告语言（用于 log_language=follow_report 时解析）
    """
    # 确定控制台日志级别
    if console_level is not None:
        level = console_level
    else:
        level = logging.DEBUG if debug else logging.INFO

    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 日志文件路径（按日期分文件）
    today_str = datetime.now().strftime('%Y%m%d')
    log_file = log_path / f"{log_prefix}_{today_str}.log"
    debug_log_file = log_path / f"{log_prefix}_debug_{today_str}.log"

    # 配置根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 根 logger 设为 DEBUG，由 handler 控制输出级别

    # 清除已有 handler，避免重复添加
    if root_logger.handlers:
        root_logger.handlers.clear()
    # 创建相对路径 Formatter（相对于项目根目录）
    project_root = Path.cwd()
    rel_formatter = RelativePathFormatter(
        LOG_FORMAT,
        LOG_DATE_FORMAT,
        relative_to=project_root,
        log_language=log_language,
        report_language=report_language,
    )
    # Handler 1: 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(rel_formatter)
    root_logger.addHandler(console_handler)

    # Handler 2: 常规日志文件（INFO 级别，10MB 轮转）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(rel_formatter)
    root_logger.addHandler(file_handler)

    # Handler 3: 调试日志文件（DEBUG 级别，包含所有详细信息）
    debug_handler = RotatingFileHandler(
        debug_log_file,
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=3,
        encoding='utf-8'
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(rel_formatter)
    root_logger.addHandler(debug_handler)

    # 降低第三方库的日志级别
    quiet_loggers = DEFAULT_QUIET_LOGGERS.copy()
    if extra_quiet_loggers:
        quiet_loggers.extend(extra_quiet_loggers)

    for logger_name in quiet_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # 输出初始化完成信息（使用相对路径）
    try:
        rel_log_path = log_path.resolve().relative_to(project_root)
    except ValueError:
        rel_log_path = log_path

    try:
        rel_log_file = log_file.resolve().relative_to(project_root)
    except ValueError:
        rel_log_file = log_file

    try:
        rel_debug_log_file = debug_log_file.resolve().relative_to(project_root)
    except ValueError:
        rel_debug_log_file = debug_log_file

    logging.info(f"日志系统初始化完成，日志目录: {rel_log_path}")
    logging.info(f"常规日志: {rel_log_file}")
    logging.info(f"调试日志: {rel_debug_log_file}")
