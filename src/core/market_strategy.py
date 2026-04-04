# -*- coding: utf-8 -*-
"""Market strategy blueprints for CN/US daily market recap."""

from dataclasses import dataclass
from typing import List

from src.report_language import normalize_report_language


@dataclass(frozen=True)
class StrategyDimension:
    """Single strategy dimension used by market recap prompts."""

    name: str
    objective: str
    checkpoints: List[str]


@dataclass(frozen=True)
class MarketStrategyBlueprint:
    """Region specific market strategy blueprint."""

    region: str
    title: str
    positioning: str
    principles: List[str]
    dimensions: List[StrategyDimension]
    action_framework: List[str]

    def to_prompt_block(self, language: str | None = None) -> str:
        """Render blueprint as prompt instructions."""
        normalized_language = (
            normalize_report_language(language)
            if language is not None
            else ("en" if self.region == "us" else "zh")
        )
        if self.region == "cn" and normalized_language == "en":
            principles_text = "\n".join([
                "- Read index direction first, then turnover structure, then sector persistence.",
                "- Every conclusion must map to position sizing, pacing, and risk control.",
                "- Use only same-day market data and recent news; do not invent unverified details.",
            ])
            dimensions_text = "\n".join([
                "- Trend Structure: Determine whether the market is advancing, range-bound, or defensive.\n"
                "  - Are the Shanghai, Shenzhen, and ChiNext indices aligned\n"
                "  - Was the move confirmed by volume expansion or contraction\n"
                "  - Were key support or resistance levels reclaimed or lost",
                "- Flows and Sentiment: Measure short-term risk appetite.\n"
                "  - Advance/decline and limit-up/limit-down structure\n"
                "  - Whether total turnover expanded\n"
                "  - Whether crowded leaders started to diverge",
                "- Leading Themes: Identify tradeable leaders and avoid weak areas.\n"
                "  - Whether leading sectors have event catalysts\n"
                "  - Whether sector leadership is concentrated and persistent\n"
                "  - Whether lagging sectors are broadening",
            ])
            action_text = "\n".join([
                "- Offensive: index alignment higher + turnover expansion + stronger core themes.",
                "- Balanced: index divergence or low-volume range; control size and wait for confirmation.",
                "- Defensive: index weakness + broader laggards; prioritize risk control and de-risking.",
            ])
            return (
                "## Strategy Blueprint: China Market Three-Stage Recap\n"
                "Focus on index trend, capital rotation, and sector leadership to produce the next-session plan.\n\n"
                f"### Strategy Principles\n{principles_text}\n\n"
                f"### Analysis Dimensions\n{dimensions_text}\n\n"
                f"### Action Framework\n{action_text}"
            )

        principles_text = "\n".join([f"- {item}" for item in self.principles])
        action_text = "\n".join([f"- {item}" for item in self.action_framework])

        dims = []
        for dim in self.dimensions:
            checkpoints = "\n".join([f"  - {cp}" for cp in dim.checkpoints])
            dims.append(f"- {dim.name}: {dim.objective}\n{checkpoints}")
        dimensions_text = "\n".join(dims)

        return (
            f"## Strategy Blueprint: {self.title}\n"
            f"{self.positioning}\n\n"
            f"### Strategy Principles\n{principles_text}\n\n"
            f"### Analysis Dimensions\n{dimensions_text}\n\n"
            f"### Action Framework\n{action_text}"
        )

    def to_markdown_block(self, language: str | None = None) -> str:
        """Render blueprint as markdown section for template fallback report."""
        normalized_language = (
            normalize_report_language(language)
            if language is not None
            else ("en" if self.region == "us" else "zh")
        )
        if self.region == "cn" and normalized_language == "en":
            dims = "\n".join([
                "- **Trend Structure**: classify the market as advancing, range-bound, or defensive",
                "- **Flows and Sentiment**: track breadth, turnover, and crowding risk",
                "- **Leading Themes**: identify durable leaders and fragile laggards",
            ])
            return f"### VI. Strategy Framework\n{dims}\n"

        dims = "\n".join([f"- **{dim.name}**: {dim.objective}" for dim in self.dimensions])
        section_title = "### 六、策略框架" if normalized_language == "zh" else "### VI. Strategy Framework"
        return f"{section_title}\n{dims}\n"


CN_BLUEPRINT = MarketStrategyBlueprint(
    region="cn",
    title="A股市场三段式复盘策略",
    positioning="聚焦指数趋势、资金博弈与板块轮动，形成次日交易计划。",
    principles=[
        "先看指数方向，再看量能结构，最后看板块持续性。",
        "结论必须映射到仓位、节奏与风险控制动作。",
        "判断使用当日数据与近3日新闻，不臆测未验证信息。",
    ],
    dimensions=[
        StrategyDimension(
            name="趋势结构",
            objective="判断市场处于上升、震荡还是防守阶段。",
            checkpoints=["上证/深证/创业板是否同向", "放量上涨或缩量下跌是否成立", "关键支撑阻力是否被突破"],
        ),
        StrategyDimension(
            name="资金情绪",
            objective="识别短线风险偏好与情绪温度。",
            checkpoints=["涨跌家数与涨跌停结构", "成交额是否扩张", "高位股是否出现分歧"],
        ),
        StrategyDimension(
            name="主线板块",
            objective="提炼可交易主线与规避方向。",
            checkpoints=["领涨板块是否具备事件催化", "板块内部是否有龙头带动", "领跌板块是否扩散"],
        ),
    ],
    action_framework=[
        "进攻：指数共振上行 + 成交额放大 + 主线强化。",
        "均衡：指数分化或缩量震荡，控制仓位并等待确认。",
        "防守：指数转弱 + 领跌扩散，优先风控与减仓。",
    ],
)

US_BLUEPRINT = MarketStrategyBlueprint(
    region="us",
    title="US Market Regime Strategy",
    positioning="Focus on index trend, macro narrative, and sector rotation to define next-session risk posture.",
    principles=[
        "Read market regime from S&P 500, Nasdaq, and Dow alignment first.",
        "Separate beta move from theme-driven alpha rotation.",
        "Translate recap into actionable risk-on/risk-off stance with clear invalidation points.",
    ],
    dimensions=[
        StrategyDimension(
            name="Trend Regime",
            objective="Classify the market as momentum, range, or risk-off.",
            checkpoints=[
                "Are SPX/NDX/DJI directionally aligned",
                "Did volume confirm the move",
                "Are key index levels reclaimed or lost",
            ],
        ),
        StrategyDimension(
            name="Macro & Flows",
            objective="Map policy/rates narrative into equity risk appetite.",
            checkpoints=[
                "Treasury yield and USD implications",
                "Breadth and leadership concentration",
                "Defensive vs growth factor rotation",
            ],
        ),
        StrategyDimension(
            name="Sector Themes",
            objective="Identify persistent leaders and vulnerable laggards.",
            checkpoints=[
                "AI/semiconductor/software trend persistence",
                "Energy/financials sensitivity to macro data",
                "Volatility signals from VIX and large-cap earnings",
            ],
        ),
    ],
    action_framework=[
        "Risk-on: broad index breakout with expanding participation.",
        "Neutral: mixed index signals; focus on selective relative strength.",
        "Risk-off: failed breakouts and rising volatility; prioritize capital preservation.",
    ],
)


def get_market_strategy_blueprint(region: str) -> MarketStrategyBlueprint:
    """Return strategy blueprint by market region."""
    return US_BLUEPRINT if region == "us" else CN_BLUEPRINT
