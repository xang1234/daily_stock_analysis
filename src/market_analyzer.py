# -*- coding: utf-8 -*-
"""
===================================
大盘复盘分析模块
===================================

职责：
1. 获取大盘指数数据（上证、深证、创业板）
2. 搜索市场新闻形成复盘情报
3. 使用大模型生成每日大盘复盘报告
"""

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

import pandas as pd

from src.config import get_config
from src.search_service import SearchService
from src.core.market_profile import get_profile, MarketProfile
from src.core.market_strategy import get_market_strategy_blueprint
from src.report_language import (
    get_report_labels,
    localize_market_term,
    normalize_report_language,
)
from data_provider.base import DataFetcherManager

logger = logging.getLogger(__name__)


@dataclass
class MarketIndex:
    """大盘指数数据"""
    code: str                    # 指数代码
    name: str                    # 指数名称
    current: float = 0.0         # 当前点位
    change: float = 0.0          # 涨跌点数
    change_pct: float = 0.0      # 涨跌幅(%)
    open: float = 0.0            # 开盘点位
    high: float = 0.0            # 最高点位
    low: float = 0.0             # 最低点位
    prev_close: float = 0.0      # 昨收点位
    volume: float = 0.0          # 成交量（手）
    amount: float = 0.0          # 成交额（元）
    amplitude: float = 0.0       # 振幅(%)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'name': self.name,
            'current': self.current,
            'change': self.change,
            'change_pct': self.change_pct,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'volume': self.volume,
            'amount': self.amount,
            'amplitude': self.amplitude,
        }


@dataclass
class MarketOverview:
    """市场概览数据"""
    date: str                           # 日期
    indices: List[MarketIndex] = field(default_factory=list)  # 主要指数
    up_count: int = 0                   # 上涨家数
    down_count: int = 0                 # 下跌家数
    flat_count: int = 0                 # 平盘家数
    limit_up_count: int = 0             # 涨停家数
    limit_down_count: int = 0           # 跌停家数
    total_amount: float = 0.0           # 两市成交额（亿元）
    # north_flow: float = 0.0           # 北向资金净流入（亿元）- 已废弃，接口不可用
    
    # 板块涨幅榜
    top_sectors: List[Dict] = field(default_factory=list)     # 涨幅前5板块
    bottom_sectors: List[Dict] = field(default_factory=list)  # 跌幅前5板块


class MarketAnalyzer:
    """
    大盘复盘分析器
    
    功能：
    1. 获取大盘指数实时行情
    2. 获取市场涨跌统计
    3. 获取板块涨跌榜
    4. 搜索市场新闻
    5. 生成大盘复盘报告
    """
    
    def __init__(
        self,
        search_service: Optional[SearchService] = None,
        analyzer=None,
        region: str = "cn",
        report_language: Optional[str] = None,
    ):
        """
        初始化大盘分析器

        Args:
            search_service: 搜索服务实例
            analyzer: AI分析器实例（用于调用LLM）
            region: 市场区域 cn=A股 us=美股
        """
        self.config = get_config()
        self.search_service = search_service
        self.analyzer = analyzer
        self.data_manager = DataFetcherManager()
        self.region = region if region in ("cn", "us") else "cn"
        self.profile: MarketProfile = get_profile(self.region)
        self.strategy = get_market_strategy_blueprint(self.region)
        self.report_language = normalize_report_language(
            report_language or getattr(self.config, "report_language", "zh")
        )
        self.labels = get_report_labels(self.report_language)

    def get_market_overview(self) -> MarketOverview:
        """
        获取市场概览数据
        
        Returns:
            MarketOverview: 市场概览数据对象
        """
        today = datetime.now().strftime('%Y-%m-%d')
        overview = MarketOverview(date=today)
        
        # 1. 获取主要指数行情（按 region 切换 A 股/美股）
        overview.indices = self._get_main_indices()

        # 2. 获取涨跌统计（A 股有，美股无等效数据）
        if self.profile.has_market_stats:
            self._get_market_statistics(overview)

        # 3. 获取板块涨跌榜（A 股有，美股暂无）
        if self.profile.has_sector_rankings:
            self._get_sector_rankings(overview)
        
        # 4. 获取北向资金（可选）
        # self._get_north_flow(overview)
        
        return overview

    
    def _get_main_indices(self) -> List[MarketIndex]:
        """获取主要指数实时行情"""
        indices = []

        try:
            logger.info("[大盘] 获取主要指数实时行情...")

            # 使用 DataFetcherManager 获取指数行情（按 region 切换）
            data_list = self.data_manager.get_main_indices(region=self.region)

            if data_list:
                for item in data_list:
                    index = MarketIndex(
                        code=item['code'],
                        name=item['name'],
                        current=item['current'],
                        change=item['change'],
                        change_pct=item['change_pct'],
                        open=item['open'],
                        high=item['high'],
                        low=item['low'],
                        prev_close=item['prev_close'],
                        volume=item['volume'],
                        amount=item['amount'],
                        amplitude=item['amplitude']
                    )
                    indices.append(index)

            if not indices:
                logger.warning("[大盘] 所有行情数据源失败，将依赖新闻搜索进行分析")
            else:
                logger.info(f"[大盘] 获取到 {len(indices)} 个指数行情")

        except Exception as e:
            logger.error(f"[大盘] 获取指数行情失败: {e}")

        return indices

    def _get_market_statistics(self, overview: MarketOverview):
        """获取市场涨跌统计"""
        try:
            logger.info("[大盘] 获取市场涨跌统计...")

            stats = self.data_manager.get_market_stats()

            if stats:
                overview.up_count = stats.get('up_count', 0)
                overview.down_count = stats.get('down_count', 0)
                overview.flat_count = stats.get('flat_count', 0)
                overview.limit_up_count = stats.get('limit_up_count', 0)
                overview.limit_down_count = stats.get('limit_down_count', 0)
                overview.total_amount = stats.get('total_amount', 0.0)

                logger.info(f"[大盘] 涨:{overview.up_count} 跌:{overview.down_count} 平:{overview.flat_count} "
                          f"涨停:{overview.limit_up_count} 跌停:{overview.limit_down_count} "
                          f"成交额:{overview.total_amount:.0f}亿")

        except Exception as e:
            logger.error(f"[大盘] 获取涨跌统计失败: {e}")

    def _get_sector_rankings(self, overview: MarketOverview):
        """获取板块涨跌榜"""
        try:
            logger.info("[大盘] 获取板块涨跌榜...")

            top_sectors, bottom_sectors = self.data_manager.get_sector_rankings(5)

            if top_sectors or bottom_sectors:
                overview.top_sectors = top_sectors
                overview.bottom_sectors = bottom_sectors

                logger.info(f"[大盘] 领涨板块: {[s['name'] for s in overview.top_sectors]}")
                logger.info(f"[大盘] 领跌板块: {[s['name'] for s in overview.bottom_sectors]}")

        except Exception as e:
            logger.error(f"[大盘] 获取板块涨跌榜失败: {e}")
    
    # def _get_north_flow(self, overview: MarketOverview):
    #     """获取北向资金流入"""
    #     try:
    #         logger.info("[大盘] 获取北向资金...")
    #         
    #         # 获取北向资金数据
    #         df = ak.stock_hsgt_north_net_flow_in_em(symbol="北上")
    #         
    #         if df is not None and not df.empty:
    #             # 取最新一条数据
    #             latest = df.iloc[-1]
    #             if '当日净流入' in df.columns:
    #                 overview.north_flow = float(latest['当日净流入']) / 1e8  # 转为亿元
    #             elif '净流入' in df.columns:
    #                 overview.north_flow = float(latest['净流入']) / 1e8
    #                 
    #             logger.info(f"[大盘] 北向资金净流入: {overview.north_flow:.2f}亿")
    #             
    #     except Exception as e:
    #         logger.warning(f"[大盘] 获取北向资金失败: {e}")
    
    def search_market_news(self) -> List[Dict]:
        """
        搜索市场新闻
        
        Returns:
            新闻列表
        """
        if not self.search_service:
            logger.warning("[大盘] 搜索服务未配置，跳过新闻搜索")
            return []
        
        all_news = []

        # 按 region 使用不同的新闻搜索词
        search_queries = self.profile.news_queries
        
        try:
            logger.info("[大盘] 开始搜索市场新闻...")
            
            # 根据 region 设置搜索上下文名称，避免美股搜索被解读为 A 股语境
            market_name = "大盘" if self.region == "cn" else "US market"
            for query in search_queries:
                response = self.search_service.search_stock_news(
                    stock_code="market",
                    stock_name=market_name,
                    max_results=3,
                    focus_keywords=query.split()
                )
                if response and response.results:
                    all_news.extend(response.results)
                    logger.info(f"[大盘] 搜索 '{query}' 获取 {len(response.results)} 条结果")
            
            logger.info(f"[大盘] 共获取 {len(all_news)} 条市场新闻")
            
        except Exception as e:
            logger.error(f"[大盘] 搜索市场新闻失败: {e}")
        
        return all_news
    
    def generate_market_review(self, overview: MarketOverview, news: List) -> str:
        """
        使用大模型生成大盘复盘报告
        
        Args:
            overview: 市场概览数据
            news: 市场新闻列表 (SearchResult 对象列表)
            
        Returns:
            大盘复盘报告文本
        """
        if not self.analyzer or not self.analyzer.is_available():
            logger.warning("[大盘] AI分析器未配置或不可用，使用模板生成报告")
            return self._generate_template_review(overview, news)
        
        # 构建 Prompt
        prompt = self._build_review_prompt(overview, news)
        system_prompt = self._get_review_system_prompt()
        
        logger.info("[大盘] 调用大模型生成复盘报告...")
        # Use the public generate_text() entry point — never access private analyzer attributes.
        review = self.analyzer.generate_text(
            prompt,
            max_tokens=8192,
            temperature=0.7,
            system_prompt=system_prompt,
        )

        if review:
            logger.info("[大盘] 复盘报告生成成功，长度: %d 字符", len(review))
            # Inject structured data tables into LLM prose sections
            return self._inject_data_into_review(review, overview)
        else:
            logger.warning("[大盘] 大模型返回为空，使用模板报告")
            return self._generate_template_review(overview, news)

    def _get_review_system_prompt(self) -> str:
        """Return a language-aware system prompt for market review generation."""
        if self.report_language == "en":
            return (
                "You are a professional cross-market strategist. "
                "Use only the supplied market data and news, do not invent levels or events, "
                "and return concise Markdown only."
            )
        return (
            "你是一位专业的跨市场策略分析师。"
            "只能基于提供的市场数据和新闻生成复盘，不得编造指数点位或事件，"
            "并且只返回简洁的 Markdown。"
        )
    
    def _inject_data_into_review(self, review: str, overview: MarketOverview) -> str:
        """Inject structured data tables into the corresponding LLM prose sections."""
        # Build data blocks
        stats_block = self._build_stats_block(overview)
        indices_block = self._build_indices_block(overview)
        sector_block = self._build_sector_block(overview)

        summary_heading = (
            self.labels["market_summary_section"]
            if self.report_language == "en"
            else "一、市场总结"
        )
        index_heading = (
            self.labels["index_commentary_section"]
            if self.report_language == "en"
            else "二、指数点评"
        )
        sector_heading = (
            self.labels["sector_highlights_section"]
            if self.report_language == "en"
            else "四、热点解读"
        )

        if stats_block:
            review = self._insert_after_section(review, rf'###\s*(?:\d+\.\s*)?{re.escape(summary_heading)}', stats_block)

        if indices_block:
            review = self._insert_after_section(review, rf'###\s*(?:\d+\.\s*)?{re.escape(index_heading)}', indices_block)

        if sector_block:
            review = self._insert_after_section(review, rf'###\s*(?:\d+\.\s*)?{re.escape(sector_heading)}', sector_block)

        return review

    @staticmethod
    def _insert_after_section(text: str, heading_pattern: str, block: str) -> str:
        """Insert a data block at the end of a markdown section (before the next ### heading)."""
        import re
        # Find the heading
        match = re.search(heading_pattern, text)
        if not match:
            return text
        start = match.end()
        # Find the next ### heading after this one
        next_heading = re.search(r'\n###\s', text[start:])
        if next_heading:
            insert_pos = start + next_heading.start()
        else:
            # No next heading — append at end
            insert_pos = len(text)
        # Insert the block before the next heading, with spacing
        return text[:insert_pos].rstrip() + '\n\n' + block + '\n\n' + text[insert_pos:].lstrip('\n')

    def _build_stats_block(self, overview: MarketOverview) -> str:
        """Build market statistics block."""
        has_stats = overview.up_count or overview.down_count or overview.total_amount
        if not has_stats:
            return ""
        stats_line = self.labels["market_stats_line"].format(
            up=overview.up_count,
            down=overview.down_count,
            flat=overview.flat_count,
            limit_up=overview.limit_up_count,
            limit_down=overview.limit_down_count,
            amount=overview.total_amount,
        )
        lines = [f"> 📈 {stats_line}"]
        return "\n".join(lines)

    def _build_indices_block(self, overview: MarketOverview) -> str:
        """Build index snapshot table."""
        if not overview.indices:
            return ""
        lines = [
            self.labels["market_review_indices_header"],
            "|------|------|--------|-----------|",
        ]
        for idx in overview.indices:
            arrow = "🔴" if idx.change_pct < 0 else "🟢" if idx.change_pct > 0 else "⚪"
            amount_raw = idx.amount or 0.0
            if amount_raw == 0.0:
                amount_str = "N/A"
            elif amount_raw > 1e6:
                amount_str = f"{amount_raw / 1e8:.0f}"
            else:
                amount_str = f"{amount_raw:.0f}"
            index_name = localize_market_term(idx.name, self.report_language)
            lines.append(f"| {index_name} | {idx.current:.2f} | {arrow} {idx.change_pct:+.2f}% | {amount_str} |")
        return "\n".join(lines)

    def _build_sector_block(self, overview: MarketOverview) -> str:
        """Build sector ranking block."""
        if not overview.top_sectors and not overview.bottom_sectors:
            return ""
        lines = []
        if overview.top_sectors:
            top = " | ".join(
                [f"**{localize_market_term(s['name'], self.report_language)}**({s['change_pct']:+.2f}%)" for s in overview.top_sectors[:5]]
            )
            lines.append(f"> 🔥 {self.labels['leading_sectors_label']}: {top}")
        if overview.bottom_sectors:
            bot = " | ".join(
                [f"**{localize_market_term(s['name'], self.report_language)}**({s['change_pct']:+.2f}%)" for s in overview.bottom_sectors[:5]]
            )
            lines.append(f"> 💧 {self.labels['lagging_sectors_label']}: {bot}")
        return "\n".join(lines)

    def _build_review_prompt(self, overview: MarketOverview, news: List) -> str:
        """Build a language-aware market review prompt."""
        indices_lines = []
        for idx in overview.indices:
            direction = "↑" if idx.change_pct > 0 else "↓" if idx.change_pct < 0 else "-"
            index_name = localize_market_term(idx.name, self.report_language)
            indices_lines.append(f"- {index_name}: {idx.current:.2f} ({direction}{abs(idx.change_pct):.2f}%)")
        indices_text = "\n".join(indices_lines)

        top_sectors_text = ", ".join(
            [f"{localize_market_term(s['name'], self.report_language)}({s['change_pct']:+.2f}%)" for s in overview.top_sectors[:3]]
        )
        bottom_sectors_text = ", ".join(
            [f"{localize_market_term(s['name'], self.report_language)}({s['change_pct']:+.2f}%)" for s in overview.bottom_sectors[:3]]
        )

        news_lines = []
        for i, n in enumerate(news[:6], 1):
            if hasattr(n, 'title'):
                title = n.title[:80] if n.title else ''
                snippet = n.snippet[:120] if n.snippet else ''
            else:
                title = str(n.get('title', ''))[:80]
                snippet = str(n.get('snippet', ''))[:120]
            news_lines.append(f"{i}. {title}\n   {snippet}")
        news_text = "\n".join(news_lines)

        strategy_block = self.strategy.to_prompt_block(language=self.report_language)
        is_en = self.report_language == "en"
        market_title = "China A-share" if self.region == "cn" else "US"
        index_hint = (
            "Analyze the Shanghai Composite, Shenzhen Component, ChiNext, and other key mainland indices."
            if self.region == "cn" and is_en
            else (
                "Analyze the S&P 500, Nasdaq, Dow, and other major US indices."
                if is_en
                else self.profile.prompt_index_hint
            )
        )

        if is_en:
            stats_block = (
                "## Market Overview\n"
                f"- Up: {overview.up_count} | Down: {overview.down_count} | Flat: {overview.flat_count}\n"
                f"- Limit Up: {overview.limit_up_count} | Limit Down: {overview.limit_down_count}\n"
                f"- Turnover (CNY bn): {overview.total_amount:.0f}"
                if self.profile.has_market_stats
                else "## Market Overview\n- Advance/decline statistics are not available for this market."
            )
            sector_block = (
                "## Sector Performance\n"
                f"- Leading: {top_sectors_text or 'N/A'}\n"
                f"- Lagging: {bottom_sectors_text or 'N/A'}"
                if self.profile.has_sector_rankings
                else "## Sector Performance\n- Sector ranking data is not available for this market."
            )
            data_no_indices_hint = (
                "Note: market data retrieval failed. Lean mainly on the news section for qualitative analysis and do not invent index levels."
                if not indices_text
                else ""
            )
            indices_placeholder = indices_text or "No index data (API error)"
            news_placeholder = news_text or "No relevant market news"
            return f"""You are a professional market analyst. Produce a concise {market_title} market recap report from the supplied data.

[Requirements]
- Output pure Markdown only
- No JSON
- No code blocks
- Use English throughout the report
- Use emoji sparingly in headings (at most one per heading)

---

# Today's Market Data

## Date
{overview.date}

## Major Indices
{indices_placeholder}

{stats_block}

{sector_block}

## Market News
{news_placeholder}

{data_no_indices_hint}

{strategy_block}

---

# Output Template (follow this structure)

## {overview.date} {market_title} Market Review

### 1. {self.labels['market_summary_section']}
(2-3 sentences summarizing the session, index moves, and turnover profile.)

### 2. {self.labels['index_commentary_section']}
({index_hint})

### 3. {self.labels['fund_flows_section']}
(Interpret turnover and participation signals.)

### 4. {self.labels['sector_highlights_section']}
(Explain the drivers behind leading and lagging themes.)

### 5. {self.labels['outlook_section']}
(State the short-term outlook for the next session.)

### 6. {self.labels['risk_alerts_section']}
(List the key risks to monitor next.)

### 7. {self.labels['strategy_plan_section']}
(State offensive / balanced / defensive stance, position-sizing guidance, one invalidation trigger, and end with “For reference only, not investment advice.”)

---

Output the report content directly, with no extra commentary.
"""

        stats_block = (
            f"""## 市场概况
- 上涨: {overview.up_count} 家 | 下跌: {overview.down_count} 家 | 平盘: {overview.flat_count} 家
- 涨停: {overview.limit_up_count} 家 | 跌停: {overview.limit_down_count} 家
- 两市成交额: {overview.total_amount:.0f} 亿元"""
            if self.profile.has_market_stats
            else "## 市场概况\n（该市场暂无涨跌家数等统计）"
        )
        sector_block = (
            f"""## 板块表现
领涨: {top_sectors_text if top_sectors_text else "暂无数据"}
领跌: {bottom_sectors_text if bottom_sectors_text else "暂无数据"}"""
            if self.profile.has_sector_rankings
            else "## 板块表现\n（该市场暂无板块涨跌数据）"
        )
        data_no_indices_hint = (
            "注意：由于行情数据获取失败，请主要根据【市场新闻】进行定性分析和总结，不要编造具体的指数点位。"
            if not indices_text
            else ""
        )
        indices_placeholder = indices_text or "暂无指数数据（接口异常）"
        news_placeholder = news_text or "暂无相关新闻"

        return f"""你是一位专业的市场分析师，请根据以下数据生成一份简洁的大盘复盘报告。

【重要】输出要求：
- 必须输出纯 Markdown 文本格式
- 禁止输出 JSON 格式
- 禁止输出代码块
- 全文必须使用中文
- emoji 仅在标题处少量使用（每个标题最多 1 个）

---

# 今日市场数据

## 日期
{overview.date}

## 主要指数
{indices_placeholder}

{stats_block}

{sector_block}

## 市场新闻
{news_placeholder}

{data_no_indices_hint}

{strategy_block}

---

# 输出格式模板（请严格按此格式输出）

## {overview.date} 大盘复盘

### 一、{self.labels['market_summary_section']}
（2-3 句话概括今日整体表现，包括指数涨跌和成交量变化）

### 二、{self.labels['index_commentary_section']}
（{index_hint}）

### 三、{self.labels['fund_flows_section']}
（解读成交额和参与度变化的含义）

### 四、{self.labels['sector_highlights_section']}
（分析领涨领跌板块背后的逻辑和驱动因素）

### 五、{self.labels['outlook_section']}
（结合走势和新闻，给出下一交易日展望）

### 六、{self.labels['risk_alerts_section']}
（指出需要重点关注的风险）

### 七、{self.labels['strategy_plan_section']}
（给出进攻 / 均衡 / 防守结论、对应仓位建议、一个失效触发条件，并以“建议仅供参考，不构成投资建议。”结尾）

---

请直接输出复盘报告内容，不要输出其他说明文字。
"""
    
    def _generate_template_review(self, overview: MarketOverview, news: List) -> str:
        """Generate a localized fallback review when the LLM is unavailable."""
        mood_code = self.profile.mood_index_code
        mood_index = next(
            (
                idx
                for idx in overview.indices
                if idx.code == mood_code or idx.code.endswith(mood_code)
            ),
            None,
        )
        is_en = self.report_language == "en"
        if mood_index:
            if mood_index.change_pct > 1:
                market_mood = "strong advance" if is_en else "强势上涨"
            elif mood_index.change_pct > 0:
                market_mood = "mild gain" if is_en else "小幅上涨"
            elif mood_index.change_pct > -1:
                market_mood = "mild decline" if is_en else "小幅下跌"
            else:
                market_mood = "sharp decline" if is_en else "明显下跌"
        else:
            market_mood = "range-bound consolidation" if is_en else "震荡整理"

        indices_lines = []
        for idx in overview.indices[:4]:
            direction = "↑" if idx.change_pct > 0 else "↓" if idx.change_pct < 0 else "-"
            index_name = localize_market_term(idx.name, self.report_language)
            indices_lines.append(f"- **{index_name}**: {idx.current:.2f} ({direction}{abs(idx.change_pct):.2f}%)")
        indices_text = "\n".join(indices_lines)

        top_text = ", ".join([localize_market_term(s['name'], self.report_language) for s in overview.top_sectors[:3]])
        bottom_text = ", ".join([localize_market_term(s['name'], self.report_language) for s in overview.bottom_sectors[:3]])
        strategy_summary = self.strategy.to_markdown_block(language=self.report_language)

        if is_en:
            stats_section = ""
            if self.profile.has_market_stats:
                stats_section = f"""
### 3. Breadth and Turnover
| Metric | Value |
|------|------|
| Advancers | {overview.up_count} |
| Decliners | {overview.down_count} |
| Limit Up | {overview.limit_up_count} |
| Limit Down | {overview.limit_down_count} |
| Turnover (CNY bn) | {overview.total_amount:.0f} |
"""
            sector_section = ""
            if self.profile.has_sector_rankings and (top_text or bottom_text):
                sector_section = f"""
### 4. Sector Performance
- **Leading**: {top_text or 'N/A'}
- **Lagging**: {bottom_text or 'N/A'}
"""
            market_label = "China A-share" if self.region == "cn" else "US"
            return f"""## {overview.date} {market_label} Market Review

### 1. Market Summary
The {market_label.lower()} session showed a **{market_mood}** tone.

### 2. Major Indices
{indices_text or '- N/A'}
{stats_section}
{sector_section}
### 5. Risk Alerts
Markets remain risky. This fallback review is for reference only and is not investment advice.

{strategy_summary}

---
*{self.labels['market_review_generated_at_label']}: {datetime.now().strftime('%H:%M')}*
"""

        stats_section = ""
        if self.profile.has_market_stats:
            stats_section = f"""
### 三、涨跌统计
| 指标 | 数值 |
|------|------|
| 上涨家数 | {overview.up_count} |
| 下跌家数 | {overview.down_count} |
| 涨停 | {overview.limit_up_count} |
| 跌停 | {overview.limit_down_count} |
| 两市成交额 | {overview.total_amount:.0f}亿 |
"""
        sector_section = ""
        if self.profile.has_sector_rankings and (top_text or bottom_text):
            sector_section = f"""
### 四、板块表现
- **领涨**: {top_text or '暂无数据'}
- **领跌**: {bottom_text or '暂无数据'}
"""
        market_label = "A股" if self.region == "cn" else "美股"
        return f"""## {overview.date} 大盘复盘

### 一、市场总结
今日{market_label}市场整体呈现**{market_mood}**态势。

### 二、主要指数
{indices_text or '- 暂无数据'}
{stats_section}
{sector_section}
### 五、风险提示
市场有风险，投资需谨慎。以上数据仅供参考，不构成投资建议。

{strategy_summary}

---
*{self.labels['market_review_generated_at_label']}: {datetime.now().strftime('%H:%M')}*
"""
    
    def run_daily_review(self) -> str:
        """
        执行每日大盘复盘流程
        
        Returns:
            复盘报告文本
        """
        logger.info("========== 开始大盘复盘分析 ==========")
        
        # 1. 获取市场概览
        overview = self.get_market_overview()
        
        # 2. 搜索市场新闻
        news = self.search_market_news()
        
        # 3. 生成复盘报告
        report = self.generate_market_review(overview, news)
        
        logger.info("========== 大盘复盘分析完成 ==========")
        
        return report


# 测试入口
if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    )
    
    analyzer = MarketAnalyzer()
    
    # 测试获取市场概览
    overview = analyzer.get_market_overview()
    print(f"\n=== 市场概览 ===")
    print(f"日期: {overview.date}")
    print(f"指数数量: {len(overview.indices)}")
    for idx in overview.indices:
        print(f"  {idx.name}: {idx.current:.2f} ({idx.change_pct:+.2f}%)")
    print(f"上涨: {overview.up_count} | 下跌: {overview.down_count}")
    print(f"成交额: {overview.total_amount:.0f}亿")
    
    # 测试生成模板报告
    report = analyzer._generate_template_review(overview, [])
    print(f"\n=== 复盘报告 ===")
    print(report)
