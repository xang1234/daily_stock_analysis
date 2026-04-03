# -*- coding: utf-8 -*-
"""
===================================
AI Stock Analysis System - Main Scheduler
===================================

Responsibilities:
1. Coordinate the end-to-end stock analysis workflow across modules
2. Run low-concurrency thread-pool scheduling
3. Handle global exceptions so one stock failure does not break the whole run
4. Provide the CLI entrypoint

Usage:
    python main.py              # Normal run
    python main.py --debug      # Debug mode
    python main.py --dry-run    # Fetch data only, skip AI analysis

Trading principles baked into the analysis:
- Strict entry discipline: do not chase; avoid buys when deviation > 5%
- Trend trading: only trade MA5 > MA10 > MA20 bull alignment
- Efficiency first: prefer stocks with healthier chip concentration
- Entry preference: low-volume pullbacks to MA5 / MA10 support
"""
import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import dotenv_values
from src.config import setup_env

_INITIAL_PROCESS_ENV = dict(os.environ)
setup_env()

# Proxy config: controlled by USE_PROXY, disabled by default
# Proxy setup is automatically skipped in GitHub Actions
if os.getenv("GITHUB_ACTIONS") != "true" and os.getenv("USE_PROXY", "false").lower() == "true":
    # Local development environment: enable the proxy from .env if configured
    proxy_host = os.getenv("PROXY_HOST", "127.0.0.1")
    proxy_port = os.getenv("PROXY_PORT", "10809")
    proxy_url = f"http://{proxy_host}:{proxy_port}"
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url

import argparse
import logging
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Tuple

from data_provider.base import canonical_stock_code
from src.webui_frontend import prepare_webui_frontend_assets
from src.config import get_config, Config
from src.logging_config import setup_logging


logger = logging.getLogger(__name__)
_RUNTIME_ENV_FILE_KEYS = set()


def _get_active_env_path() -> Path:
    env_file = os.getenv("ENV_FILE")
    if env_file:
        return Path(env_file)
    return Path(__file__).resolve().parent / ".env"


def _read_active_env_values() -> Optional[Dict[str, str]]:
    env_path = _get_active_env_path()
    if not env_path.exists():
        return {}

    try:
        values = dotenv_values(env_path)
    except Exception as exc:  # pragma: no cover - defensive branch
        logger.warning("Failed to read config file %s; continuing with current environment variables: %s", env_path, exc)
        return None

    return {
        str(key): "" if value is None else str(value)
        for key, value in values.items()
        if key is not None
    }


_ACTIVE_ENV_FILE_VALUES = _read_active_env_values() or {}
_RUNTIME_ENV_FILE_KEYS = {
    key for key in _ACTIVE_ENV_FILE_VALUES
    if key not in _INITIAL_PROCESS_ENV
}

# setup_env() already ran at import time above.
_env_bootstrapped = True


def _bootstrap_environment() -> None:
    """Load .env and apply optional local proxy settings.

    Guarded to be idempotent so it can safely be called from lazy-import
    paths used by API / bot consumers.
    """
    global _env_bootstrapped
    if _env_bootstrapped:
        return

    from src.config import setup_env

    setup_env()

    if os.getenv("GITHUB_ACTIONS") != "true" and os.getenv("USE_PROXY", "false").lower() == "true":
        proxy_host = os.getenv("PROXY_HOST", "127.0.0.1")
        proxy_port = os.getenv("PROXY_PORT", "10809")
        proxy_url = f"http://{proxy_host}:{proxy_port}"
        os.environ["http_proxy"] = proxy_url
        os.environ["https_proxy"] = proxy_url

    _env_bootstrapped = True


def _setup_bootstrap_logging(debug: bool = False) -> None:
    """Initialize stderr-only logging before config is loaded.

    File handlers are deferred until ``config.log_dir`` is known (via the
    subsequent ``setup_logging()`` call) so that healthy runs never create
    log files in a hard-coded directory.
    """
    level = logging.DEBUG if debug else logging.INFO
    root = logging.getLogger()
    root.setLevel(level)
    if not any(
        isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stderr
        for h in root.handlers
    ):
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        root.addHandler(handler)


def _get_stock_analysis_pipeline():
    """Lazily import StockAnalysisPipeline for external consumers.

    Also ensures env/proxy bootstrap has run so that API / bot consumers
    that never call ``main()`` still get ``USE_PROXY`` applied.
    """
    _bootstrap_environment()
    from src.core.pipeline import StockAnalysisPipeline as _Pipeline

    return _Pipeline


class _LazyPipelineDescriptor:
    """Descriptor that resolves StockAnalysisPipeline on first attribute access."""

    _resolved = None

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, obj, objtype=None):
        if self._resolved is None:
            self._resolved = _get_stock_analysis_pipeline()
        return self._resolved


class _ModuleExports:
    StockAnalysisPipeline = _LazyPipelineDescriptor()


_exports = _ModuleExports()


def __getattr__(name: str):
    if name == "StockAnalysisPipeline":
        return _exports.StockAnalysisPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _reload_env_file_values_preserving_overrides() -> None:
    """Refresh `.env`-managed env vars without clobbering process env overrides."""
    global _RUNTIME_ENV_FILE_KEYS

    latest_values = _read_active_env_values()
    if latest_values is None:
        return

    managed_keys = {
        key for key in latest_values
        if key not in _INITIAL_PROCESS_ENV
    }

    for key in _RUNTIME_ENV_FILE_KEYS - managed_keys:
        os.environ.pop(key, None)

    for key in managed_keys:
        os.environ[key] = latest_values[key]

    _RUNTIME_ENV_FILE_KEYS = managed_keys


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='AI Stock Analysis System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python main.py                    # Normal run
  python main.py --debug            # Debug mode
  python main.py --dry-run          # Fetch data only, skip AI analysis
  python main.py --stocks 600519,000001  # Analyze specific stocks
  python main.py --no-notify        # Disable push notifications
  python main.py --single-notify    # Notify after each stock instead of sending an aggregate report
  python main.py --schedule         # Enable scheduled mode
  python main.py --market-review    # Run market review only
        '''
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode with verbose logging'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch data only, without running AI analysis'
    )

    parser.add_argument(
        '--stocks',
        type=str,
        help='Comma-separated stock codes to analyze (overrides config)'
    )

    parser.add_argument(
        '--no-notify',
        action='store_true',
        help='Do not send push notifications'
    )

    parser.add_argument(
        '--single-notify',
        action='store_true',
        help='Enable per-stock notifications instead of sending a combined report'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Worker count (defaults to config value)'
    )

    parser.add_argument(
        '--schedule',
        action='store_true',
        help='Enable scheduled mode and run daily at the configured time'
    )

    parser.add_argument(
        '--no-run-immediately',
        action='store_true',
        help='Do not run once immediately when scheduled mode starts'
    )

    parser.add_argument(
        '--market-review',
        action='store_true',
        help='Run market review only'
    )

    parser.add_argument(
        '--no-market-review',
        action='store_true',
        help='Skip market review'
    )

    parser.add_argument(
        '--force-run',
        action='store_true',
        help='Skip the trading-day check and force a full run (Issue #373)'
    )

    parser.add_argument(
        '--webui',
        action='store_true',
        help='Start the Web management UI'
    )

    parser.add_argument(
        '--webui-only',
        action='store_true',
        help='Start the Web service only, without running analysis'
    )

    parser.add_argument(
        '--serve',
        action='store_true',
        help='Start the FastAPI backend and run analysis'
    )

    parser.add_argument(
        '--serve-only',
        action='store_true',
        help='Start the FastAPI backend only, without auto-running analysis'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='FastAPI service port (default: 8000)'
    )

    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='FastAPI bind address (default: 0.0.0.0)'
    )

    parser.add_argument(
        '--no-context-snapshot',
        action='store_true',
        help='Do not save analysis context snapshots'
    )

    # === Backtest ===
    parser.add_argument(
        '--backtest',
        action='store_true',
        help='Run backtesting against historical analysis results'
    )

    parser.add_argument(
        '--backtest-code',
        type=str,
        default=None,
        help='Backtest only the specified stock code'
    )

    parser.add_argument(
        '--backtest-days',
        type=int,
        default=None,
        help='Backtest evaluation window in trading days (defaults to config)'
    )

    parser.add_argument(
        '--backtest-force',
        action='store_true',
        help='Force backtesting even if results already exist'
    )

    return parser.parse_args()


def _compute_trading_day_filter(
    config: Config,
    args: argparse.Namespace,
    stock_codes: List[str],
) -> Tuple[List[str], Optional[str], bool]:
    """
    Compute filtered stock list and effective market review region (Issue #373).

    Returns:
        (filtered_codes, effective_region, should_skip_all)
        - effective_region None = use config default (check disabled)
        - effective_region '' = all relevant markets closed, skip market review
        - should_skip_all: skip entire run when no stocks and no market review to run
    """
    force_run = getattr(args, 'force_run', False)
    if force_run or not getattr(config, 'trading_day_check_enabled', True):
        return (stock_codes, None, False)

    from src.core.trading_calendar import (
        get_market_for_stock,
        get_open_markets_today,
        compute_effective_region,
    )

    open_markets = get_open_markets_today()
    filtered_codes = []
    for code in stock_codes:
        mkt = get_market_for_stock(code)
        if mkt in open_markets or mkt is None:
            filtered_codes.append(code)

    if config.market_review_enabled and not getattr(args, 'no_market_review', False):
        effective_region = compute_effective_region(
            getattr(config, 'market_review_region', 'cn') or 'cn', open_markets
        )
    else:
        effective_region = None

    should_skip_all = (not filtered_codes) and (effective_region or '') == ''
    return (filtered_codes, effective_region, should_skip_all)


def run_full_analysis(
    config: Config,
    args: argparse.Namespace,
    stock_codes: Optional[List[str]] = None
):
    """
    Run the full analysis flow (stocks + market review).

    This is the main entrypoint used by scheduled runs.
    """
    # Import pipeline modules outside the broad try/except so that import-time
    # failures propagate to the caller instead of being silently swallowed.
    from src.core.market_review import run_market_review
    from src.core.pipeline import StockAnalysisPipeline

    try:
        # Issue #529: Hot-reload STOCK_LIST from .env on each scheduled run
        if stock_codes is None:
            config.refresh_stock_list()

        # Issue #373: Trading day filter (per-stock, per-market)
        effective_codes = stock_codes if stock_codes is not None else config.stock_list
        filtered_codes, effective_region, should_skip = _compute_trading_day_filter(
            config, args, effective_codes
        )
        if should_skip:
            logger.info(
                "All relevant markets are closed today. Skipping this run. Use --force-run to override."
            )
            return
        if set(filtered_codes) != set(effective_codes):
            skipped = set(effective_codes) - set(filtered_codes)
            logger.info("Skipped stocks that are in closed markets today: %s", skipped)
        stock_codes = filtered_codes

        # CLI flag --single-notify overrides config (#55)
        if getattr(args, 'single_notify', False):
            config.single_stock_notify = True

        # Issue #190: merge stock analysis and market review into one notification
        merge_notification = (
            getattr(config, 'merge_email_notification', False)
            and config.market_review_enabled
            and not getattr(args, 'no_market_review', False)
            and not config.single_stock_notify
        )

        # Create the pipeline
        save_context_snapshot = None
        if getattr(args, 'no_context_snapshot', False):
            save_context_snapshot = False
        query_id = uuid.uuid4().hex
        pipeline = StockAnalysisPipeline(
            config=config,
            max_workers=args.workers,
            query_id=query_id,
            query_source="cli",
            save_context_snapshot=save_context_snapshot
        )

        # 1. Run stock analysis
        results = pipeline.run(
            stock_codes=stock_codes,
            dry_run=args.dry_run,
            send_notification=not args.no_notify,
            merge_notification=merge_notification
        )

        # Issue #128: add a delay between stock analysis and market review
        analysis_delay = getattr(config, 'analysis_delay', 0)
        if (
            analysis_delay > 0
            and config.market_review_enabled
            and not args.no_market_review
            and effective_region != ''
        ):
            logger.info("Waiting %s seconds before market review to avoid API rate limits...", analysis_delay)
            time.sleep(analysis_delay)

        # 2. Run market review if enabled and not explicitly skipped
        market_report = ""
        if (
            config.market_review_enabled
            and not args.no_market_review
            and effective_region != ''
        ):
            review_result = run_market_review(
                notifier=pipeline.notifier,
                analyzer=pipeline.analyzer,
                search_service=pipeline.search_service,
                send_notification=not args.no_notify,
                merge_notification=merge_notification,
                override_region=effective_region,
            )
            # Preserve the result for later Feishu doc generation
            if review_result:
                market_report = review_result

        # Issue #190: send a merged notification for stocks + market review
        if merge_notification and (results or market_report) and not args.no_notify:
            parts = []
            if market_report:
                parts.append(f"# 📈 大盘复盘\n\n{market_report}")
            if results:
                dashboard_content = pipeline.notifier.generate_aggregate_report(
                    results,
                    getattr(config, 'report_type', 'simple'),
                )
                parts.append(f"# 🚀 个股决策仪表盘\n\n{dashboard_content}")
            if parts:
                combined_content = "\n\n---\n\n".join(parts)
                if pipeline.notifier.is_available():
                    if pipeline.notifier.send(combined_content, email_send_to_all=True):
                        logger.info("Sent merged notification for stock analysis and market review")
                    else:
                        logger.warning("Failed to send merged notification")

        # Print a summary
        if results:
            logger.info("\n===== Analysis Summary =====")
            for r in sorted(results, key=lambda x: x.sentiment_score, reverse=True):
                emoji = r.get_emoji()
                logger.info(
                    f"{emoji} {r.name}({r.code}): {r.operation_advice} | "
                    f"Score {r.sentiment_score} | {r.trend_prediction}"
                )

        logger.info("\nRun completed")

        # === Generate Feishu Docs output ===
        try:
            from src.feishu_doc import FeishuDocManager

            feishu_doc = FeishuDocManager()
            if feishu_doc.is_configured() and (results or market_report):
                logger.info("Creating Feishu cloud document...")

                # 1. Prepare the title, e.g. "2026-01-01 13:01 大盘复盘"
                tz_cn = timezone(timedelta(hours=8))
                now = datetime.now(tz_cn)
                doc_title = f"{now.strftime('%Y-%m-%d %H:%M')} 大盘复盘"

                # 2. Build the content from stock analysis and market review
                full_content = ""

                # Add market review content if available
                if market_report:
                    full_content += f"# 📈 大盘复盘\n\n{market_report}\n\n---\n\n"

                # Add the stock dashboard generated by NotificationService
                if results:
                    dashboard_content = pipeline.notifier.generate_aggregate_report(
                        results,
                        getattr(config, 'report_type', 'simple'),
                    )
                    full_content += f"# 🚀 个股决策仪表盘\n\n{dashboard_content}"

                # 3. Create the document
                doc_url = feishu_doc.create_daily_doc(doc_title, full_content)
                if doc_url:
                    logger.info("Feishu cloud document created successfully: %s", doc_url)
                    # Optionally push the document link to chat channels as well
                    if not args.no_notify:
                        pipeline.notifier.send(f"[{now.strftime('%Y-%m-%d %H:%M')}] 复盘文档创建成功: {doc_url}")

        except Exception as e:
            logger.error("Failed to generate Feishu document: %s", e)

        # === Auto backtest ===
        try:
            if getattr(config, 'backtest_enabled', False):
                from src.services.backtest_service import BacktestService

                logger.info("Starting automatic backtest...")
                service = BacktestService()
                stats = service.run_backtest(
                    force=False,
                    eval_window_days=getattr(config, 'backtest_eval_window_days', 10),
                    min_age_days=getattr(config, 'backtest_min_age_days', 14),
                    limit=200,
                )
                logger.info(
                    f"Automatic backtest completed: processed={stats.get('processed')} saved={stats.get('saved')} "
                    f"completed={stats.get('completed')} insufficient={stats.get('insufficient')} errors={stats.get('errors')}"
                )
        except Exception as e:
            logger.warning("Automatic backtest failed and was ignored: %s", e)

    except Exception as e:
        logger.exception("Analysis pipeline failed: %s", e)


def start_api_server(host: str, port: int, config: Config) -> None:
    """
    Start the FastAPI server in a background thread.

    Args:
        host: Bind address
        port: Bind port
        config: Config object
    """
    import threading
    import uvicorn

    def run_server():
        level_name = (config.log_level or "INFO").lower()
        uvicorn.run(
            "api.app:app",
            host=host,
            port=port,
            log_level=level_name,
            log_config=None,
        )

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    logger.info("FastAPI server started: http://%s:%s", host, port)


def _is_truthy_env(var_name: str, default: str = "true") -> bool:
    """Parse common truthy / falsy environment values."""
    value = os.getenv(var_name, default).strip().lower()
    return value not in {"0", "false", "no", "off"}


def start_bot_stream_clients(config: Config) -> None:
    """Start bot stream clients when enabled in config."""
    # Start the DingTalk Stream client
    if config.dingtalk_stream_enabled:
        try:
            from bot.platforms import start_dingtalk_stream_background, DINGTALK_STREAM_AVAILABLE
            if DINGTALK_STREAM_AVAILABLE:
                if start_dingtalk_stream_background():
                    logger.info("[Main] Dingtalk Stream client started in background.")
                else:
                    logger.warning("[Main] Dingtalk Stream client failed to start.")
            else:
                logger.warning("[Main] Dingtalk Stream enabled but SDK is missing.")
                logger.warning("[Main] Run: pip install dingtalk-stream")
        except Exception as exc:
            logger.error(f"[Main] Failed to start Dingtalk Stream client: {exc}")

    # Start the Feishu Stream client
    if getattr(config, 'feishu_stream_enabled', False):
        try:
            from bot.platforms import start_feishu_stream_background, FEISHU_SDK_AVAILABLE
            if FEISHU_SDK_AVAILABLE:
                if start_feishu_stream_background():
                    logger.info("[Main] Feishu Stream client started in background.")
                else:
                    logger.warning("[Main] Feishu Stream client failed to start.")
            else:
                logger.warning("[Main] Feishu Stream enabled but SDK is missing.")
                logger.warning("[Main] Run: pip install lark-oapi")
        except Exception as exc:
            logger.error(f"[Main] Failed to start Feishu Stream client: {exc}")


def _resolve_scheduled_stock_codes(stock_codes: Optional[List[str]]) -> Optional[List[str]]:
    """Scheduled runs should always read the latest persisted watchlist."""
    if stock_codes is not None:
        logger.warning(
            "Detected --stocks in scheduled mode; scheduled runs will ignore the startup snapshot and reload the latest STOCK_LIST before each run."
        )
    return None


def _reload_runtime_config() -> Config:
    """Reload config from the latest persisted `.env` values for scheduled runs."""
    _reload_env_file_values_preserving_overrides()
    Config.reset_instance()
    return get_config()


def _build_schedule_time_provider(default_schedule_time: str):
    """Read the latest schedule time directly from the active config file.

    Fallback order:
    1. Process-level env override (set before launch) → honour it.
    2. Persisted config file value (written by WebUI) → use it.
    3. Documented system default ``"18:00"`` → always fall back here so
       that clearing SCHEDULE_TIME in WebUI correctly resets the schedule.
    """
    from src.core.config_manager import ConfigManager

    _SYSTEM_DEFAULT_SCHEDULE_TIME = "18:00"
    manager = ConfigManager()

    def _provider() -> str:
        if "SCHEDULE_TIME" in _INITIAL_PROCESS_ENV:
            return os.getenv("SCHEDULE_TIME", default_schedule_time)

        config_map = manager.read_config_map()
        schedule_time = (config_map.get("SCHEDULE_TIME", "") or "").strip()
        if schedule_time:
            return schedule_time
        return _SYSTEM_DEFAULT_SCHEDULE_TIME

    return _provider


def main() -> int:
    """
    Main entrypoint.

    Returns:
        Exit code (0 means success)
    """
    # Parse CLI arguments
    args = parse_arguments()

    # Initialize bootstrap logging before config loading so early failures are still captured
    try:
        _setup_bootstrap_logging(debug=args.debug)
    except Exception as exc:
        logging.basicConfig(
            level=logging.DEBUG if getattr(args, "debug", False) else logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            stream=sys.stderr,
        )
        logger.warning("Bootstrap logging initialization failed; fell back to stderr: %s", exc)

    # Load config after bootstrap logging so config failures are logged
    try:
        config = get_config()
    except Exception as exc:
        logger.exception("Failed to load config: %s", exc)
        return 1

    # Configure logging to both console and file
    try:
        setup_logging(log_prefix="stock_analysis", debug=args.debug, log_dir=config.log_dir)
    except Exception as exc:
        logger.exception("Failed to switch to the configured log directory: %s", exc)
        return 1

    logger.info("=" * 60)
    logger.info("AI Stock Analysis System started")
    logger.info("Run time: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    logger.info("=" * 60)

    # Validate config
    warnings = config.validate()
    for warning in warnings:
        logger.warning(warning)

    # Parse the stock list (normalized to uppercase, Issue #355)
    stock_codes = None
    if args.stocks:
        stock_codes = [canonical_stock_code(c) for c in args.stocks.split(',') if (c or "").strip()]
        logger.info("Using stock list from CLI arguments: %s", stock_codes)

    # === Map --webui / --webui-only to --serve / --serve-only ===
    if args.webui:
        args.serve = True
    if args.webui_only:
        args.serve_only = True

    # Backward compatibility for the legacy WEBUI_ENABLED env var
    if config.webui_enabled and not (args.serve or args.serve_only):
        args.serve = True

    # === Start the Web service if enabled ===
    start_serve = (args.serve or args.serve_only) and os.getenv("GITHUB_ACTIONS") != "true"

    # Backward compatibility for WEBUI_HOST / WEBUI_PORT if --host / --port are not provided
    if start_serve:
        if args.host == '0.0.0.0' and os.getenv('WEBUI_HOST'):
            args.host = os.getenv('WEBUI_HOST')
        if args.port == 8000 and os.getenv('WEBUI_PORT'):
            args.port = int(os.getenv('WEBUI_PORT'))

    bot_clients_started = False
    if start_serve:
        if not prepare_webui_frontend_assets():
            logger.warning("Frontend static assets are not ready; continuing to start FastAPI, but the Web UI may be unavailable")
        try:
            start_api_server(host=args.host, port=args.port, config=config)
            bot_clients_started = True
        except Exception as e:
            logger.error("Failed to start FastAPI service: %s", e)

    if bot_clients_started:
        start_bot_stream_clients(config)

    # === Web-service-only mode: do not run analysis automatically ===
    if args.serve_only:
        logger.info("Mode: Web service only")
        logger.info("Web service running at: http://%s:%s", args.host, args.port)
        logger.info("Trigger analysis via /api/v1/analysis/analyze")
        logger.info("API docs: http://%s:%s/docs", args.host, args.port)
        logger.info("Press Ctrl+C to exit...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nInterrupted by user; exiting")
        return 0

    try:
        # Mode 0: backtest
        if getattr(args, 'backtest', False):
            logger.info("Mode: Backtest")
            from src.services.backtest_service import BacktestService

            service = BacktestService()
            stats = service.run_backtest(
                code=getattr(args, 'backtest_code', None),
                force=getattr(args, 'backtest_force', False),
                eval_window_days=getattr(args, 'backtest_days', None),
            )
            logger.info(
                f"Backtest completed: processed={stats.get('processed')} saved={stats.get('saved')} "
                f"completed={stats.get('completed')} insufficient={stats.get('insufficient')} errors={stats.get('errors')}"
            )
            return 0

        # Mode 1: market review only
        if args.market_review:
            from src.analyzer import GeminiAnalyzer
            from src.core.market_review import run_market_review
            from src.notification import NotificationService
            from src.search_service import SearchService

            # Issue #373: Trading day check for market-review-only mode.
            # Do NOT use _compute_trading_day_filter here: that helper checks
            # config.market_review_enabled, which would wrongly block an
            # explicit --market-review invocation when the flag is disabled.
            effective_region = None
            if not getattr(args, 'force_run', False) and getattr(config, 'trading_day_check_enabled', True):
                from src.core.trading_calendar import get_open_markets_today, compute_effective_region as _compute_region
                open_markets = get_open_markets_today()
                effective_region = _compute_region(
                    getattr(config, 'market_review_region', 'cn') or 'cn', open_markets
                )
                if effective_region == '':
                    logger.info("All markets relevant to market review are closed today. Skipping. Use --force-run to override.")
                    return 0

            logger.info("Mode: Market review only")
            notifier = NotificationService()

            # Initialize the search service and analyzer if configured
            search_service = None
            analyzer = None

            if config.has_search_capability_enabled():
                search_service = SearchService(
                    bocha_keys=config.bocha_api_keys,
                    tavily_keys=config.tavily_api_keys,
                    brave_keys=config.brave_api_keys,
                    serpapi_keys=config.serpapi_keys,
                    minimax_keys=config.minimax_api_keys,
                    searxng_base_urls=config.searxng_base_urls,
                    searxng_public_instances_enabled=config.searxng_public_instances_enabled,
                    news_max_age_days=config.news_max_age_days,
                    news_strategy_profile=getattr(config, "news_strategy_profile", "short"),
                )

            if config.gemini_api_key or config.openai_api_key:
                analyzer = GeminiAnalyzer(api_key=config.gemini_api_key)
                if not analyzer.is_available():
                    logger.warning("AI analyzer is unavailable after initialization; check your API key configuration")
                    analyzer = None
            else:
                logger.warning("No API key detected (Gemini/OpenAI); falling back to template-only report generation")

            run_market_review(
                notifier=notifier,
                analyzer=analyzer,
                search_service=search_service,
                send_notification=not args.no_notify,
                override_region=effective_region,
            )
            return 0

        # Mode 2: scheduled mode
        if args.schedule or config.schedule_enabled:
            logger.info("Mode: Scheduled")
            logger.info("Daily run time: %s", config.schedule_time)

            # Determine whether to run immediately:
            # Command line arg --no-run-immediately overrides config if present.
            # Otherwise use config (defaults to True).
            should_run_immediately = config.schedule_run_immediately
            if getattr(args, 'no_run_immediately', False):
                should_run_immediately = False

            logger.info("Run immediately on startup: %s", should_run_immediately)

            from src.scheduler import run_with_schedule
            scheduled_stock_codes = _resolve_scheduled_stock_codes(stock_codes)
            schedule_time_provider = _build_schedule_time_provider(config.schedule_time)

            def scheduled_task():
                runtime_config = _reload_runtime_config()
                run_full_analysis(runtime_config, args, scheduled_stock_codes)

            background_tasks = []
            if getattr(config, 'agent_event_monitor_enabled', False):
                from src.agent.events import build_event_monitor_from_config, run_event_monitor_once

                monitor = build_event_monitor_from_config(config)
                if monitor is not None:
                    interval_minutes = max(1, getattr(config, 'agent_event_monitor_interval_minutes', 5))

                    def event_monitor_task():
                        triggered = run_event_monitor_once(monitor)
                        if triggered:
                                logger.info("[EventMonitor] Triggered %d reminders in this cycle", len(triggered))

                    background_tasks.append({
                        "task": event_monitor_task,
                        "interval_seconds": interval_minutes * 60,
                        "run_immediately": True,
                        "name": "agent_event_monitor",
                    })
                else:
                    logger.info("EventMonitor is enabled, but no valid rules were loaded; skipping the background reminder task")

            run_with_schedule(
                task=scheduled_task,
                schedule_time=config.schedule_time,
                run_immediately=should_run_immediately,
                background_tasks=background_tasks,
                schedule_time_provider=schedule_time_provider,
            )
            return 0

        # Mode 3: normal one-off run
        if config.run_immediately:
            run_full_analysis(config, args, stock_codes)
        else:
            logger.info("Configured not to run analysis immediately (RUN_IMMEDIATELY=false)")

        logger.info("\nProgram completed")

        # If the service is enabled and this is not scheduled mode, keep the process alive
        keep_running = start_serve and not (args.schedule or config.schedule_enabled)
        if keep_running:
            logger.info("API service is still running (press Ctrl+C to exit)...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

        return 0

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user; exiting")
        return 130

    except Exception as e:
        logger.exception("Program execution failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
