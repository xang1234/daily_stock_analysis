<div align="center">

# AI Stock Analysis System

[![GitHub stars](https://img.shields.io/github/stars/ZhuLinsen/daily_stock_analysis?style=social)](https://github.com/ZhuLinsen/daily_stock_analysis/stargazers)
[![CI](https://github.com/ZhuLinsen/daily_stock_analysis/actions/workflows/ci.yml/badge.svg)](https://github.com/ZhuLinsen/daily_stock_analysis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Ready-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://hub.docker.com/)

<p>
  <a href="https://trendshift.io/repositories/18527" target="_blank"><img src="https://trendshift.io/api/badge/repositories/18527" alt="ZhuLinsen%2Fdaily_stock_analysis | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
  <a href="https://hellogithub.com/repository/ZhuLinsen/daily_stock_analysis" target="_blank"><img src="https://api.hellogithub.com/v1/widgets/recommend.svg?rid=6daa16e405ce46ed97b4a57706aeb29f&claim_uid=pfiJMqhR9uvDGlT&theme=neutral" alt="Featured｜HelloGitHub" style="width: 250px; height: 54px;" width="250" height="54" /></a>
</p>

> AI-powered watchlist analysis for A-shares, Hong Kong stocks, and US stocks. Run daily analysis, generate a decision dashboard, and push results to WeCom, Feishu, Telegram, Discord, Slack, or email.

[**Key Features**](#-key-features) · [**Quick Start**](#-quick-start) · [**Sample Output**](#-sample-output) · [**Full Guide**](docs/full-guide_EN.md) · [**FAQ**](docs/FAQ_EN.md) · [**Changelog**](docs/CHANGELOG.md)

English | [繁體中文](docs/README_CHT.md)

</div>

## 💖 Sponsors
<div align="center">
  <a href="https://serpapi.com/baidu-search-api?utm_source=github_daily_stock_analysis" target="_blank">
    <img src="./sources/serpapi_banner_en.png" alt="Easily scrape real-time financial news data from search engines - SerpApi" height="160">
  </a>
</div>
<br>

## ✨ Key Features

| Module | Feature | Description |
|------|------|------|
| AI | Decision Dashboard | One-line conclusion, precise entry/exit levels, and an action checklist |
| Analysis | Multi-dimensional Analysis | Intraday MA alignment, chip distribution, sentiment intel, and real-time quotes |
| Market | Global Market Coverage | Supports A-shares, Hong Kong stocks, US stocks, and US indices such as `SPX`, `DJI`, and `IXIC` |
| Fundamentals | Structured Aggregation | Adds `fundamental_context` with `valuation`, `growth`, `earnings`, `institution`, `capital_flow`, `dragon_tiger`, and `boards`; the main pipeline remains fail-open |
| Strategy | Market Strategy System | Built-in A-share three-stage review strategy and US regime strategy with attack/balance/defense or risk-on/neutral/risk-off plans |
| Review | Market Review | Daily market overview, gainers/losers, and `cn` / `us` / `both` review modes |
| UI | Dual-theme Workspace | Unified light and dark themes across Home, Ask, Backtest, Portfolio, and Settings |
| Search | Smart Autocomplete (MVP) | Search by code, company name, pinyin, or aliases across A-share, Hong Kong, and US markets |
| Import | Smart Multi-source Import | Import from image, CSV/Excel, or pasted tables with Vision extraction and confidence-based review |
| History | Batch Management | Multi-select, select all, and batch delete for historical analysis records |
| Backtest | AI Backtest Validation | Compare AI predictions with next-session results using a 1-day evaluation window |
| Intel | Announcements + Capital Flow | IntelAgent pulls announcements from SSE/SZSE/cninfo and A-share main-force capital flow |
| Agent | Strategy Chat | Multi-turn strategy Q&A with 11 built-in strategies across Web, Bot, and API |
| Notifications | Multi-channel Delivery | WeCom, Feishu, Telegram, Discord, Slack, DingTalk, email, Pushover, and more |
| Automation | Scheduled Execution | Run on GitHub Actions without maintaining a server |

> Historical report details now prioritize the raw "sniper levels" text returned by the model so that ranges and conditional notes are not collapsed into a single number.

> The Backtest page includes a "next-session / 1-day window" view that lets you filter by stock and analysis date range, compare the original prediction with the next trading day move, and inspect the interval accuracy rate. It is based on historical analysis plus 1-day backtest data, not actual trade execution logs.

> The Web workspace has completed a UI refresh. Light mode is now fully supported, theme switching is persistent, and the Home, Ask, Backtest, Portfolio, and Settings pages share one design system.

> Ask mode also improved message copy/export, notification sending, history deletion, and follow-up context protection. Copy feedback, empty states, and error states are now isolated per panel to avoid state leakage.

> Web admin authentication supports runtime enable/disable. If an admin password already exists, re-enabling authentication requires the current password to prevent taking over the session while auth is temporarily disabled. In multi-process deployments, the toggle only takes effect in the current worker until all workers are restarted.

> Portfolio management now validates available holdings before recording a sell. Overselling is rejected. If historical trades, cash ledger entries, or corporate actions were entered incorrectly, you can delete them directly from the `/portfolio` event list to rebuild the snapshot. Under concurrent writes, the direct portfolio write API may return `409 portfolio_busy`; CSV import still keeps per-row submission and partial-success semantics.

### Tech Stack & Data Sources

| Type | Supported |
|------|------|
| LLMs | [AIHubMix](https://aihubmix.com/?aff=CfMq), Gemini, OpenAI-compatible providers, DeepSeek, Qwen, Claude, Ollama, and other LiteLLM-backed models |
| Market Data | AkShare, Tushare, Pytdx, Baostock, YFinance, [Longbridge](https://open.longbridge.com/) |
| News Search | Tavily, SerpAPI, Bocha, Brave, MiniMax |
| Social Sentiment | [Stock Sentiment API](https://api.adanos.org/docs) for Reddit / X / Polymarket on US stocks |

> **Longbridge-first for US/HK only:** when `LONGBRIDGE_APP_KEY`, `LONGBRIDGE_APP_SECRET`, and `LONGBRIDGE_ACCESS_TOKEN` are configured, daily candles and real-time quotes for US and Hong Kong stocks are fetched from Longbridge first. If Longbridge fails or returns incomplete fields, the system falls back to YFinance for US stocks and AkShare for Hong Kong stocks. If Longbridge credentials are not configured, Longbridge is not called. US indices such as `SPX` still use YFinance first. A-share routing remains `Efinance -> AkShare -> Tushare -> Pytdx -> Baostock`.

### Built-in Trading Discipline

| Rule | Description |
|------|------|
| No chasing highs | Warn automatically when deviation exceeds the threshold, `5%` by default; strong momentum stocks can use a looser threshold |
| Trend trading | Bull alignment rule: `MA5 > MA10 > MA20` |
| Precise levels | Generate entry, stop-loss, and target levels |
| Checklist | Mark each item as `Pass`, `Watch`, or `Fail` |

## 🚀 Quick Start

### Option 1: GitHub Actions (Recommended)

#### 1. Fork this repository

Click the `Fork` button in the top-right corner.

#### 2. Configure Secrets

Go to your forked repository:

`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

**AI model configuration**

> For detailed provider and routing examples, see [LLM Config Guide](docs/LLM_CONFIG_GUIDE_EN.md).

| Secret Name | Description | Required |
|------|------|------|
| `GEMINI_API_KEY` | API key from [Google AI Studio](https://aistudio.google.com/) | Recommended |
| `OPENAI_API_KEY` | OpenAI-compatible API key, also usable for DeepSeek, Qwen, and similar providers | Optional |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint such as `https://api.deepseek.com/v1` | Optional |
| `OPENAI_MODEL` | Model name such as `deepseek-chat` | Optional |
| `OLLAMA_API_BASE` | Ollama service address such as `http://localhost:11434`; required for Ollama, do not reuse `OPENAI_BASE_URL` | Optional |

> Configure at least one of `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `OLLAMA_API_BASE`.

<details>
<summary><b>Notification channels</b></summary>

| Secret Name | Description | Required |
|------|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from `@BotFather` | Optional |
| `TELEGRAM_CHAT_ID` | Telegram chat ID | Optional |
| `TELEGRAM_MESSAGE_THREAD_ID` | Telegram topic ID | Optional |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL | Optional |
| `DISCORD_BOT_TOKEN` | Discord bot token | Optional |
| `DISCORD_MAIN_CHANNEL_ID` | Discord channel ID for bot mode | Optional |
| `DISCORD_INTERACTIONS_PUBLIC_KEY` | Discord public key for inbound interaction signature verification | Optional |
| `SLACK_BOT_TOKEN` | Slack bot token; preferred when both bot and webhook are set | Optional |
| `SLACK_CHANNEL_ID` | Slack channel ID for bot mode | Optional |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL; text only | Optional |
| `EMAIL_SENDER` | Sender email address | Optional |
| `EMAIL_PASSWORD` | SMTP authorization code or app password | Optional |
| `EMAIL_RECEIVERS` | Comma-separated receivers | Optional |
| `WECHAT_WEBHOOK_URL` | WeCom webhook URL | Optional |
| `FEISHU_WEBHOOK_URL` | Feishu webhook URL | Optional |
| `PUSHPLUS_TOKEN` | PushPlus token | Optional |
| `SERVERCHAN3_SENDKEY` | ServerChan v3 send key | Optional |
| `CUSTOM_WEBHOOK_URLS` | Comma-separated custom webhook URLs, including DingTalk | Optional |
| `CUSTOM_WEBHOOK_BEARER_TOKEN` | Bearer token for custom webhooks | Optional |
| `SINGLE_STOCK_NOTIFY` | Notify immediately after each stock finishes | Optional |
| `REPORT_TYPE` | `simple`, `full`, or `brief` | Optional |
| `REPORT_LANGUAGE` | `zh` or `en`; controls prompts, templates, and fixed report labels | Optional |
| `ANALYSIS_DELAY` | Delay in seconds between stocks and market review | Optional |

</details>

**Stock list and data-source configuration**

| Secret Name | Description | Required |
|------|------|------|
| `STOCK_LIST` | Watchlist, for example `600519,AAPL,hk00700` | Required |
| `TAVILY_API_KEYS` | [Tavily](https://tavily.com/) search API for news | Recommended |
| `MINIMAX_API_KEYS` | [MiniMax](https://platform.minimaxi.com/) web search | Optional |
| `SERPAPI_API_KEYS` | [SerpAPI](https://serpapi.com/baidu-search-api?utm_source=github_daily_stock_analysis) backup search | Optional |
| `BOCHA_API_KEYS` | [Bocha Search](https://open.bocha.cn/) web search API | Optional |
| `BRAVE_API_KEYS` | [Brave Search](https://brave.com/search/api/) API | Optional |
| `SEARXNG_BASE_URLS` | Self-hosted SearXNG instances; if empty, public instance discovery can be used | Optional |
| `SEARXNG_PUBLIC_INSTANCES_ENABLED` | Enable public SearXNG discovery when `SEARXNG_BASE_URLS` is empty, default `true` | Optional |
| `SOCIAL_SENTIMENT_API_KEY` | [Stock Sentiment API](https://api.adanos.org/docs) for US social sentiment | Optional |
| `SOCIAL_SENTIMENT_API_URL` | Custom social sentiment API base URL | Optional |
| `TUSHARE_TOKEN` | [Tushare Pro](https://tushare.pro/weborder/#/login?reg=834638) token | Optional |
| `TICKFLOW_API_KEY` | [TickFlow](https://tickflow.org) API key for A-share market-review enhancements | Optional |
| `LONGBRIDGE_APP_KEY` | Longbridge app key | Optional |
| `LONGBRIDGE_APP_SECRET` | Longbridge app secret | Optional |
| `LONGBRIDGE_ACCESS_TOKEN` | Longbridge access token | Optional |
| `LONGBRIDGE_STATIC_INFO_TTL_SECONDS` | In-process `static_info` cache TTL, default `86400` | Optional |
| `LONGBRIDGE_HTTP_URL` | Longbridge HTTP endpoint | Optional |
| `LONGBRIDGE_QUOTE_WS_URL` | Longbridge quote websocket endpoint | Optional |
| `LONGBRIDGE_TRADE_WS_URL` | Longbridge trade websocket endpoint | Optional |
| `LONGBRIDGE_REGION` | Region override such as `cn` or `hk` | Optional |
| `LONGBRIDGE_ENABLE_OVERNIGHT` | Enable overnight quotes, default `false` | Optional |
| `LONGBRIDGE_PUSH_CANDLESTICK_MODE` | `realtime` or `confirmed`, default `realtime` | Optional |
| `LONGBRIDGE_PRINT_QUOTE_PACKAGES` | Print quote packages on connect when set to `1`, `true`, or `yes` | Optional |
| `PREFETCH_REALTIME_QUOTES` | Disable global prefetch by setting `false`; default `true` | Optional |
| `WECHAT_MSG_TYPE` | WeCom message type, default `markdown`, or `text` | Optional |
| `NEWS_STRATEGY_PROFILE` | `ultra_short`, `short`, `medium`, or `long`; default `short` | Optional |
| `NEWS_MAX_AGE_DAYS` | Upper news age limit in days; the effective window is the smaller of profile days and this value | Optional |
| `BIAS_THRESHOLD` | Deviation threshold in percent; default `5.0` | Optional |
| `AGENT_MODE` | Enable Agent strategy chat mode, default `false` | Optional |
| `AGENT_LITELLM_MODEL` | Agent-only model; inherits the main model when empty | Optional |
| `AGENT_SKILLS` | Comma-separated strategy skill IDs or `all` | Optional |
| `AGENT_MAX_STEPS` | Max Agent reasoning steps, default `10` | Optional |
| `AGENT_SKILL_DIR` | Custom strategy-skill directory | Optional |
| `TRADING_DAY_CHECK_ENABLED` | Skip execution on non-trading days by default; set `false` to disable the check | Optional |
| `ENABLE_CHIP_DISTRIBUTION` | Enable chip distribution analysis | Optional |
| `ENABLE_FUNDAMENTAL_PIPELINE` | Global switch for the fundamentals pipeline | Optional |
| `FUNDAMENTAL_STAGE_TIMEOUT_SECONDS` | Fundamentals stage time budget | Optional |
| `FUNDAMENTAL_FETCH_TIMEOUT_SECONDS` | Per-source timeout | Optional |
| `FUNDAMENTAL_RETRY_MAX` | Max retries including the initial call | Optional |
| `FUNDAMENTAL_CACHE_TTL_SECONDS` | Fundamentals cache TTL | Optional |
| `FUNDAMENTAL_CACHE_MAX_ENTRIES` | Fundamentals cache size limit | Optional |

> Fundamentals currently use a best-effort fail-open timeout model. Timeouts degrade the stage immediately and the main workflow continues. This is a soft-timeout design, not a hard SLA.

#### 3. Enable Actions

Open `Actions` and click `I understand my workflows, go ahead and enable them`.

#### 4. Manual Test

Open `Actions` -> `Daily Stock Analysis` -> `Run workflow`.

#### Done

The workflow runs automatically at `18:00` Beijing time on trading days by default. Non-trading days across A-share, Hong Kong, and US calendars are skipped unless you disable the trading-day check or use a force-run option.

> Two skip-check mechanisms are supported. `TRADING_DAY_CHECK_ENABLED=false` changes behavior globally through environment variables or Secrets, while `force_run` only affects a single manually triggered Actions run.

> Resume fetch and `--dry-run` reuse logic resolve the latest reusable trading day based on each market's local timezone and calendar. On weekends and holidays, the previous trading day is reused. During a trading session, the latest completed trading day is reused. After close, the run can be skipped if the day's data already exists.

### Option 2: Local Run / Docker Deployment

```bash
# Clone the project
git clone https://github.com/ZhuLinsen/daily_stock_analysis.git && cd daily_stock_analysis

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env && vim .env

# Run analysis
python main.py
```

If you do not need the Web UI, defining model channels directly in `.env` is recommended:

```env
LLM_CHANNELS=primary
LLM_PRIMARY_PROTOCOL=openai
LLM_PRIMARY_BASE_URL=https://api.deepseek.com/v1
LLM_PRIMARY_API_KEY=sk-xxxxxxxx
LLM_PRIMARY_MODELS=deepseek-chat
LITELLM_MODEL=openai/deepseek-chat
```

You can still edit the same fields later from the Web settings page. No extra config file is required.

If you also enable advanced YAML routing through `LITELLM_CONFIG`, the YAML file defines available models and routing rules through `model_list`, while runtime selections such as `LITELLM_MODEL`, `LITELLM_FALLBACK_MODELS`, `VISION_MODEL`, and `LLM_TEMPERATURE` still decide which models are actively used. The channel editor only saves channel entries and does not overwrite those runtime choices.

> For Docker deployment and scheduled-task setup, see [Full Guide](docs/full-guide_EN.md).
> For the desktop client packaging flow, see [Desktop Packaging](docs/desktop-package.md).

## 📱 Sample Output

### Decision Dashboard
```text
🎯 2026-02-08 Decision Dashboard
3 stocks analyzed | 🟢Buy:0 🟡Hold:2 🔴Sell:1

📊 Analysis Summary
⚪ Zhongwu High-Tech (000657): Hold | Score 65 | Bullish
⚪ Yongding Co. (600105): Hold | Score 48 | Sideways
🟡 Xinlai Applied Materials (300260): Sell | Score 35 | Bearish

⚪ Zhongwu High-Tech (000657)
📰 Key Information
💭 Sentiment: The market is watching its AI-related narrative and strong earnings growth, but short-term profit-taking and capital outflow pressure still need to be digested.
📊 Earnings Outlook: Based on recent news and sentiment, the company's first three quarters of 2025 showed strong year-over-year growth, providing fundamental support.

🚨 Risk Alerts
Risk 1: Main-force funds saw a large net outflow on February 5.
Risk 2: Chip concentration indicates resistance may remain high.
Risk 3: News mentions historical compliance issues and restructuring-related risks.

✨ Positive Catalysts
Catalyst 1: Market positioning as a core AI server HDI supplier.
Catalyst 2: Very strong year-over-year non-recurring profit growth.

📢 Latest Update: Sentiment suggests the company is a leader in AI PCB micro-drilling and is deeply tied to leading global PCB/substrate suppliers.

---
Generated at: 18:00
```

### Market Review
```text
🎯 2026-01-10 Market Review

📊 Major Indices
- SSE Composite: 3250.12 (🟢+0.85%)
- Shenzhen Component: 10521.36 (🟢+1.02%)
- ChiNext: 2156.78 (🟢+1.35%)

📈 Market Breadth
Up: 3920 | Down: 1349 | Limit Up: 155 | Limit Down: 3

🔥 Sector Performance
Top: Internet Services, Media, Minor Metals
Bottom: Insurance, Airports, Solar Equipment
```

## ⚙️ Configuration

> For the complete environment variable list and schedule setup, see [Full Guide](docs/full-guide_EN.md).
> Email delivery currently uses SMTP authorization codes or basic authentication. If your Outlook or Exchange account requires OAuth2, the current version does not support it.

## 🖥️ Web UI

![Web UI](sources/fastapi_server.png)

The Web app includes configuration management, task monitoring, and manual analysis.

**Highlights from the latest UI refresh**

- Full light theme support instead of a dark-only workspace
- Persistent theme switching in the sidebar
- One shared visual system across Home, Ask, Backtest, Portfolio, and Settings
- Improved mobile and touch behavior for drawers, scrolling, and message actions

**Optional password protection:** set `ADMIN_AUTH_ENABLED=true` in `.env` to enable Web login. On first use, initialize the password in the UI to protect API keys and other sensitive settings. Authentication can now be enabled or disabled at runtime. Disabling auth does not delete the saved password. If auth is enabled, `POST /api/v1/auth/logout` also requires a valid session. When the session expires, the frontend returns directly to the login page.

### Smart Import

In `Settings -> Basic Settings -> Smart Import`, you can add stocks in three ways:

1. **Image**: drag in a screenshot from a broker app or watchlist and let Vision extract codes and names with confidence scores.
2. **File**: upload CSV or Excel (`.xlsx`) and parse code/name columns automatically.
3. **Paste**: paste data copied from Excel or another table and click parse.

**Preview and merge behavior**

- High-confidence items are preselected.
- Medium- and low-confidence items require manual confirmation.
- Supports deduplication by code, clear all, and select all.
- Only checked and successfully parsed items are merged.

**Requirements and limits**

- Image import requires at least one Vision-capable provider such as `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY`.
- Images: JPG, PNG, WebP, GIF, up to 5 MB.
- Files: up to 2 MB.
- Pasted text: up to 100 KB.

**APIs**

- `POST /api/v1/stocks/extract-from-image`
- `POST /api/v1/stocks/parse-import`

### Smart Search Autocomplete (MVP)

The home analysis input works like a search box:

- **Multi-signal matching**: stock code, Chinese company name, pinyin abbreviation, and aliases such as `gzmt`, `tencent`, or `aapl`
- **Multi-market coverage**: local index for A-shares, Hong Kong stocks, and US stocks
- **Graceful fallback**:
  - If the index is outdated or fails to load, the UI falls back to plain input
  - If there is no match, pressing Enter still submits the raw input directly

> To rebuild the index, use `scripts/fetch_tushare_stock_list.py` to refresh stock lists and then `scripts/generate_index_from_csv.py` to regenerate the index file. See [Tushare Stock List Guide](docs/TUSHARE_STOCK_LIST_GUIDE.md).

**LLM usage summary API**: `GET /api/v1/usage/summary?period=today|month|all`

**Analysis API note**: `POST /api/v1/analysis/analyze` supports only one stock when `async_mode=false`. Batch `stock_codes` require `async_mode=true`. For async `202` responses, a single-stock request returns `task_id`, while a batch request returns `accepted` and `duplicates`. Blank codes are filtered on the server, and a fully empty request becomes `400`. Unknown `/api` routes return JSON `404` instead of falling back to the frontend.

### Historical Report Details

From the Home page history list, choose a record and click `Full Analysis Report` to open the full Markdown report in the right drawer. It includes sentiment intel, core conclusion, data perspective, and action plan.

Two copy modes are available:

- `Copy Markdown Source`: preserve Markdown formatting for editing or archiving
- `Copy Plain Text`: strip common Markdown syntax for messaging apps and plain-text sharing

### 🤖 Agent Strategy Chat

Start the service with `AGENT_MODE=true` and open `/chat` for multi-turn strategy Q&A.

> User-facing copy still uses the word "strategy", but the internal code, configuration, and API field name use `skill`. You can think of it as a reusable strategy capability package.

- Choose from 11 built-in strategies such as MA golden cross, Chan theory, wave theory, and bull-trend analysis
- Ask in natural language, for example `Analyze 600519 with Chan theory`
- Stream intermediate progress while the Agent fetches quotes, indicators, and news
- Continue multi-turn conversations with persistent history
- Export conversations to `.md` or send them to configured notification channels
- Let analysis keep running in the background even if the page changes
- Use bot commands such as `/ask`, `/chat`, `/history`, `/strategies`, and `/research`
- Add custom strategies by placing YAML files in `strategies/` or `SKILL.md` bundles in a custom skill directory
- Enable the experimental multi-Agent flow with `AGENT_ARCH=multi` to cascade Technical -> Intel -> Risk -> Specialist -> Decision stages

> If any AI API key is configured, Agent chat becomes available automatically and does not require `AGENT_MODE=true`. To turn it off explicitly, set `AGENT_MODE=false`. Changing the main model, Agent model, fallback models, or model-channel configuration requires a service restart or a config reload before new worker processes use the updated model chain.

### Startup Methods

1. **Start the service**. By default, the frontend is built automatically.

```bash
python main.py --webui       # Start Web UI and scheduled analysis
python main.py --webui-only  # Start Web UI only
```

At startup the project runs `npm install && npm run build` in `apps/dsa-web`.

To disable auto-build, set `WEBUI_AUTO_BUILD=false` and build manually:

```bash
cd ./apps/dsa-web
npm install && npm run build
cd ../..
```

Then open `http://127.0.0.1:8000`.

> If you deploy on a cloud server and are unsure which address to open in the browser, see [Cloud Web UI Deployment Guide](docs/deploy-webui-cloud.md).
> `python main.py --serve` is also supported as an equivalent entrypoint.

## 🗺️ Roadmap

See [Changelog](docs/CHANGELOG.md) for shipped features and upcoming work.

> Suggestions are welcome through [Issues](https://github.com/ZhuLinsen/daily_stock_analysis/issues).

> The Web UI is still under active iteration. During the transition period, some pages may still have styling, interaction, or compatibility issues. Please report them through [Issues](https://github.com/ZhuLinsen/daily_stock_analysis/issues) or send a [Pull Request](https://github.com/ZhuLinsen/daily_stock_analysis/pulls).

---

## ☕ Support the Project

If this project helps you, support ongoing maintenance and iteration.

| Alipay | WeChat Pay | Xiaohongshu |
| :---: | :---: | :---: |
| <img src="./sources/alipay.jpg" width="200" alt="Alipay"> | <img src="./sources/wechatpay.jpg" width="200" alt="WeChat Pay"> | <img src="./sources/xiaohongshu.png" width="200" alt="Xiaohongshu"> |

---

## 🤝 Contributing

Issues and Pull Requests are welcome.

See [Contributing Guide](docs/CONTRIBUTING_EN.md).

### Local Gate Checks

```bash
pip install -r requirements.txt
pip install flake8 pytest
./scripts/ci_gate.sh
```

If you changed the frontend in `apps/dsa-web`:

```bash
cd apps/dsa-web
npm ci
npm run lint
npm run build
```

## 📄 License

[MIT License](LICENSE) © 2026 ZhuLinsen

If you use this project or build on top of it, adding the repository link in your README or documentation is appreciated. It helps long-term maintenance and community growth.

## 📬 Contact

- GitHub Issues: [Open an issue](https://github.com/ZhuLinsen/daily_stock_analysis/issues)
- Email: `zhuls345@gmail.com`

## ⭐ Star History

**If the project is useful, please consider giving it a star.**

<a href="https://star-history.com/#ZhuLinsen/daily_stock_analysis&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=ZhuLinsen/daily_stock_analysis&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=ZhuLinsen/daily_stock_analysis&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=ZhuLinsen/daily_stock_analysis&type=Date" />
 </picture>
</a>

## ⚠️ Disclaimer

This project is for learning and research only. It is not investment advice. The stock market involves risk, and all investment decisions remain your own responsibility.

---
