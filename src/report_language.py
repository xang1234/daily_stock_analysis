# -*- coding: utf-8 -*-
"""Helpers for report output language selection and localization."""

from __future__ import annotations

import csv
import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

SUPPORTED_REPORT_LANGUAGES = ("zh", "en")
SUPPORTED_LOG_LANGUAGES = ("zh", "en", "follow_report")

_REPORT_LANGUAGE_ALIASES = {
    "zh-cn": "zh",
    "zh_cn": "zh",
    "zh-hans": "zh",
    "zh_hans": "zh",
    "zh-tw": "zh",
    "zh_tw": "zh",
    "cn": "zh",
    "chinese": "zh",
    "english": "en",
    "en-us": "en",
    "en_us": "en",
    "en-gb": "en",
    "en_gb": "en",
}

_LOG_LANGUAGE_ALIASES = {
    **_REPORT_LANGUAGE_ALIASES,
    "follow-report": "follow_report",
    "follow_report": "follow_report",
    "followreport": "follow_report",
}

_OPERATION_ADVICE_CANONICAL_MAP = {
    "强烈买入": "strong_buy",
    "strong buy": "strong_buy",
    "strong_buy": "strong_buy",
    "买入": "buy",
    "buy": "buy",
    "加仓": "buy",
    "accumulate": "buy",
    "add position": "buy",
    "持有": "hold",
    "hold": "hold",
    "观望": "watch",
    "watch": "watch",
    "wait": "watch",
    "wait and see": "watch",
    "减仓": "reduce",
    "reduce": "reduce",
    "trim": "reduce",
    "卖出": "sell",
    "sell": "sell",
    "强烈卖出": "strong_sell",
    "strong sell": "strong_sell",
    "strong_sell": "strong_sell",
}

_OPERATION_ADVICE_TRANSLATIONS = {
    "strong_buy": {"zh": "强烈买入", "en": "Strong Buy"},
    "buy": {"zh": "买入", "en": "Buy"},
    "hold": {"zh": "持有", "en": "Hold"},
    "watch": {"zh": "观望", "en": "Watch"},
    "reduce": {"zh": "减仓", "en": "Reduce"},
    "sell": {"zh": "卖出", "en": "Sell"},
    "strong_sell": {"zh": "强烈卖出", "en": "Strong Sell"},
}

_TREND_PREDICTION_CANONICAL_MAP = {
    "强烈看多": "strong_bullish",
    "strong bullish": "strong_bullish",
    "very bullish": "strong_bullish",
    "看多": "bullish",
    "bullish": "bullish",
    "uptrend": "bullish",
    "震荡": "sideways",
    "neutral": "sideways",
    "sideways": "sideways",
    "range-bound": "sideways",
    "看空": "bearish",
    "bearish": "bearish",
    "downtrend": "bearish",
    "强烈看空": "strong_bearish",
    "strong bearish": "strong_bearish",
    "very bearish": "strong_bearish",
}

_TREND_PREDICTION_TRANSLATIONS = {
    "strong_bullish": {"zh": "强烈看多", "en": "Strong Bullish"},
    "bullish": {"zh": "看多", "en": "Bullish"},
    "sideways": {"zh": "震荡", "en": "Sideways"},
    "bearish": {"zh": "看空", "en": "Bearish"},
    "strong_bearish": {"zh": "强烈看空", "en": "Strong Bearish"},
}

_CONFIDENCE_LEVEL_CANONICAL_MAP = {
    "高": "high",
    "high": "high",
    "中": "medium",
    "medium": "medium",
    "med": "medium",
    "低": "low",
    "low": "low",
}

_CONFIDENCE_LEVEL_TRANSLATIONS = {
    "high": {"zh": "高", "en": "High"},
    "medium": {"zh": "中", "en": "Medium"},
    "low": {"zh": "低", "en": "Low"},
}

_CHIP_HEALTH_CANONICAL_MAP = {
    "健康": "healthy",
    "healthy": "healthy",
    "一般": "average",
    "average": "average",
    "警惕": "caution",
    "caution": "caution",
}

_CHIP_HEALTH_TRANSLATIONS = {
    "healthy": {"zh": "健康", "en": "Healthy"},
    "average": {"zh": "一般", "en": "Average"},
    "caution": {"zh": "警惕", "en": "Caution"},
}

_BIAS_STATUS_CANONICAL_MAP = {
    "安全": "safe",
    "safe": "safe",
    "警戒": "caution",
    "警惕": "caution",
    "caution": "caution",
    "危险": "danger",
    "risk": "danger",
    "danger": "danger",
}

_BIAS_STATUS_TRANSLATIONS = {
    "safe": {"zh": "安全", "en": "Safe"},
    "caution": {"zh": "警戒", "en": "Caution"},
    "danger": {"zh": "危险", "en": "Danger"},
}

_PLACEHOLDER_BY_LANGUAGE = {
    "zh": "待补充",
    "en": "TBD",
}

_UNKNOWN_BY_LANGUAGE = {
    "zh": "未知",
    "en": "Unknown",
}

_NO_DATA_BY_LANGUAGE = {
    "zh": "数据缺失",
    "en": "Data unavailable",
}

_GENERIC_STOCK_NAME_BY_LANGUAGE = {
    "zh": "待确认股票",
    "en": "Unnamed Stock",
}

_CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

_ENGLISH_STOCK_NAME_BY_CODE = {
    "600519": "Kweichow Moutai",
    "000001": "Ping An Bank",
    "300750": "CATL",
    "002594": "BYD",
    "600036": "China Merchants Bank",
    "601318": "Ping An Insurance",
    "000858": "Wuliangye",
    "600276": "Hengrui Pharma",
    "601012": "LONGi Green Energy",
    "002475": "Luxshare Precision",
    "300059": "East Money Information",
    "002415": "Hikvision",
    "600900": "China Yangtze Power",
    "601166": "Industrial Bank",
    "600028": "Sinopec",
    "600030": "CITIC Securities",
    "600031": "Sany Heavy Industry",
    "600050": "China Unicom",
    "600104": "SAIC Motor",
    "600111": "Northern Rare Earth",
    "600150": "CSSC",
    "600309": "Wanhua Chemical",
    "600406": "NARI Technology",
    "600690": "Haier Smart Home",
    "600760": "AVIC Shenyang Aircraft",
    "600809": "Shanxi Fenjiu",
    "600887": "Yili",
    "600930": "Huadian New Energy",
    "601088": "China Shenhua",
    "601127": "Seres",
    "601211": "Guotai Haitong",
    "601225": "Shaanxi Coal",
    "601288": "Agricultural Bank of China",
    "601328": "Bank of Communications",
    "601398": "Industrial and Commercial Bank of China",
    "601601": "CPIC",
    "601628": "China Life",
    "601658": "Postal Savings Bank of China",
    "601668": "China State Construction",
    "601728": "China Telecom",
    "601816": "Beijing-Shanghai High-Speed Railway",
    "601857": "PetroChina",
    "601888": "China Tourism Group Duty Free",
    "601899": "Zijin Mining",
    "601919": "COSCO Shipping Holdings",
    "601985": "China National Nuclear Power",
    "601988": "Bank of China",
    "603019": "Sugon",
    "603259": "WuXi AppTec",
    "603501": "Will Semiconductor",
    "603993": "CMOC",
    "688008": "Montage Technology",
    "688012": "AMEC",
    "688041": "Hygon Information Technology",
    "688111": "Kingsoft Office",
    "688256": "Cambricon",
    "688981": "SMIC",
    "AAPL": "Apple",
    "TSLA": "Tesla",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet Class A",
    "GOOG": "Alphabet Class C",
    "AMZN": "Amazon",
    "NVDA": "NVIDIA",
    "META": "Meta",
    "AMD": "AMD",
    "INTC": "Intel",
    "BABA": "Alibaba",
    "PDD": "PDD Holdings",
    "JD": "JD.com",
    "BIDU": "Baidu",
    "NIO": "NIO",
    "XPEV": "XPeng",
    "LI": "Li Auto",
    "COIN": "Coinbase",
    "MSTR": "Strategy",
    "00700": "Tencent Holdings",
    "03690": "Meituan",
    "01810": "Xiaomi",
    "09988": "Alibaba",
    "09618": "JD.com",
    "09888": "Baidu",
    "01024": "Kuaishou",
    "00981": "SMIC",
    "02015": "Li Auto",
    "09868": "XPeng",
    "00005": "HSBC Holdings",
    "01299": "AIA Group",
    "00941": "China Mobile",
    "00883": "CNOOC",
    "02513": "Zhipu AI",
    "HK02513": "Zhipu AI",
}

_ENGLISH_STOCK_NAME_BY_NAME = {
    "贵州茅台": "Kweichow Moutai",
    "平安银行": "Ping An Bank",
    "宁德时代": "CATL",
    "比亚迪": "BYD",
    "招商银行": "China Merchants Bank",
    "中国平安": "Ping An Insurance",
    "五粮液": "Wuliangye",
    "恒瑞医药": "Hengrui Pharma",
    "隆基绿能": "LONGi Green Energy",
    "立讯精密": "Luxshare Precision",
    "东方财富": "East Money Information",
    "海康威视": "Hikvision",
    "长江电力": "China Yangtze Power",
    "兴业银行": "Industrial Bank",
    "中国石化": "Sinopec",
    "中信证券": "CITIC Securities",
    "三一重工": "Sany Heavy Industry",
    "中国联通": "China Unicom",
    "上汽集团": "SAIC Motor",
    "北方稀土": "Northern Rare Earth",
    "中国船舶": "CSSC",
    "万华化学": "Wanhua Chemical",
    "国电南瑞": "NARI Technology",
    "海尔智家": "Haier Smart Home",
    "中航沈飞": "AVIC Shenyang Aircraft",
    "山西汾酒": "Shanxi Fenjiu",
    "伊利股份": "Yili",
    "华电新能": "Huadian New Energy",
    "中国神华": "China Shenhua",
    "赛力斯": "Seres",
    "国泰海通": "Guotai Haitong",
    "陕西煤业": "Shaanxi Coal",
    "农业银行": "Agricultural Bank of China",
    "交通银行": "Bank of Communications",
    "工商银行": "Industrial and Commercial Bank of China",
    "中国太保": "CPIC",
    "中国人寿": "China Life",
    "邮储银行": "Postal Savings Bank of China",
    "中国建筑": "China State Construction",
    "中国电信": "China Telecom",
    "京沪高铁": "Beijing-Shanghai High-Speed Railway",
    "中国石油": "PetroChina",
    "中国中免": "China Tourism Group Duty Free",
    "紫金矿业": "Zijin Mining",
    "中远海控": "COSCO Shipping Holdings",
    "中国核电": "China National Nuclear Power",
    "中国银行": "Bank of China",
    "中科曙光": "Sugon",
    "药明康德": "WuXi AppTec",
    "豪威集团": "Will Semiconductor",
    "洛阳钼业": "CMOC",
    "澜起科技": "Montage Technology",
    "中微公司": "AMEC",
    "海光信息": "Hygon Information Technology",
    "金山办公": "Kingsoft Office",
    "寒武纪": "Cambricon",
    "中芯国际": "SMIC",
    "苹果": "Apple",
    "特斯拉": "Tesla",
    "微软": "Microsoft",
    "谷歌A": "Alphabet Class A",
    "谷歌C": "Alphabet Class C",
    "亚马逊": "Amazon",
    "英伟达": "NVIDIA",
    "英特尔": "Intel",
    "阿里巴巴": "Alibaba",
    "拼多多": "PDD Holdings",
    "京东": "JD.com",
    "百度": "Baidu",
    "蔚来": "NIO",
    "小鹏汽车": "XPeng",
    "理想汽车": "Li Auto",
    "腾讯控股": "Tencent Holdings",
    "美团": "Meituan",
    "小米集团": "Xiaomi",
    "京东集团": "JD.com",
    "百度集团": "Baidu",
    "快手": "Kuaishou",
    "汇丰控股": "HSBC Holdings",
    "友邦保险": "AIA Group",
    "中国移动": "China Mobile",
    "中国海洋石油": "CNOOC",
    "智谱": "Zhipu AI",
}

_CN_MARKET_TERM_ALIASES = {
    "上证指数": "Shanghai Composite",
    "上证综指": "Shanghai Composite",
    "深证成指": "Shenzhen Component",
    "创业板指": "ChiNext Index",
    "科创50": "STAR 50",
    "北证50": "Beijing Stock Exchange 50",
    "沪深300": "CSI 300",
    "中证500": "CSI 500",
    "中证1000": "CSI 1000",
    "恒生指数": "Hang Seng Index",
    "恒生科技指数": "Hang Seng Tech Index",
    "国企指数": "Hang Seng China Enterprises Index",
    "人工智能": "Artificial Intelligence",
    "半导体": "Semiconductors",
    "芯片": "Chips",
    "算力": "Compute Infrastructure",
    "机器人": "Robotics",
    "消费电子": "Consumer Electronics",
    "新能源车": "NEVs",
    "锂电池": "Lithium Batteries",
    "光伏": "Solar",
    "风电": "Wind Power",
    "电力": "Power Utilities",
    "军工": "Defense",
    "医药": "Healthcare",
    "创新药": "Innovative Drugs",
    "券商": "Brokerages",
    "银行": "Banks",
    "保险": "Insurance",
    "地产": "Property",
    "煤炭": "Coal",
    "有色金属": "Nonferrous Metals",
    "稀土": "Rare Earths",
    "黄金": "Gold",
    "油气": "Oil & Gas",
    "航运": "Shipping",
    "旅游": "Travel",
    "白酒": "Baijiu",
    "食品饮料": "Food & Beverage",
}

logger = logging.getLogger(__name__)
_MISSING_MARKET_TERM_WARNINGS: set[str] = set()

_REPORT_LABELS: Dict[str, Dict[str, str]] = {
    "zh": {
        "dashboard_title": "决策仪表盘",
        "brief_title": "决策简报",
        "analyzed_prefix": "共分析",
        "stock_unit": "只股票",
        "stock_unit_compact": "只",
        "buy_label": "买入",
        "watch_label": "观望",
        "sell_label": "卖出",
        "summary_heading": "分析结果摘要",
        "info_heading": "重要信息速览",
        "sentiment_summary_label": "舆情情绪",
        "earnings_outlook_label": "业绩预期",
        "risk_alerts_label": "风险警报",
        "positive_catalysts_label": "利好催化",
        "latest_news_label": "最新动态",
        "core_conclusion_heading": "核心结论",
        "one_sentence_label": "一句话决策",
        "time_sensitivity_label": "时效性",
        "default_time_sensitivity": "本周内",
        "position_status_label": "持仓情况",
        "action_advice_label": "操作建议",
        "no_position_label": "空仓者",
        "has_position_label": "持仓者",
        "continue_holding": "继续持有",
        "market_snapshot_heading": "当日行情",
        "close_label": "收盘",
        "prev_close_label": "昨收",
        "open_label": "开盘",
        "high_label": "最高",
        "low_label": "最低",
        "change_pct_label": "涨跌幅",
        "change_amount_label": "涨跌额",
        "amplitude_label": "振幅",
        "volume_label": "成交量",
        "amount_label": "成交额",
        "current_price_label": "当前价",
        "volume_ratio_label": "量比",
        "turnover_rate_label": "换手率",
        "source_label": "行情来源",
        "data_perspective_heading": "数据透视",
        "ma_alignment_label": "均线排列",
        "bullish_alignment_label": "多头排列",
        "yes_label": "是",
        "no_label": "否",
        "trend_strength_label": "趋势强度",
        "price_metrics_label": "价格指标",
        "ma5_label": "MA5",
        "ma10_label": "MA10",
        "ma20_label": "MA20",
        "bias_ma5_label": "乖离率(MA5)",
        "support_level_label": "支撑位",
        "resistance_level_label": "压力位",
        "chip_label": "筹码",
        "battle_plan_heading": "作战计划",
        "ideal_buy_label": "理想买入点",
        "secondary_buy_label": "次优买入点",
        "stop_loss_label": "止损位",
        "take_profit_label": "目标位",
        "suggested_position_label": "仓位建议",
        "entry_plan_label": "建仓策略",
        "risk_control_label": "风控策略",
        "checklist_heading": "检查清单",
        "failed_checks_heading": "检查未通过项",
        "history_compare_heading": "历史信号对比",
        "time_label": "时间",
        "score_label": "评分",
        "advice_label": "建议",
        "trend_label": "趋势",
        "generated_at_label": "报告生成时间",
        "report_time_label": "生成时间",
        "no_results": "无分析结果",
        "report_title": "股票分析报告",
        "avg_score_label": "均分",
        "action_points_heading": "操作点位",
        "position_advice_heading": "持仓建议",
        "analysis_model_label": "分析模型",
        "not_investment_advice": "AI生成，仅供参考，不构成投资建议",
        "details_report_hint": "详细报告见",
        "confidence_label": "置信度",
        "key_points_label": "核心看点",
        "reason_label": "操作理由",
        "risk_warning_heading": "风险提示",
        "trend_analysis_heading": "走势分析",
        "outlook_heading": "市场展望",
        "short_term_outlook_label": "短期（1-3日）",
        "medium_term_outlook_label": "中期（1-2周）",
        "technical_heading": "技术面分析",
        "technical_summary_label": "综合",
        "ma_section_label": "均线",
        "volume_section_label": "量能",
        "pattern_section_label": "形态",
        "fundamental_heading": "基本面分析",
        "sector_position_label": "板块地位",
        "company_highlights_label": "公司亮点",
        "news_heading": "消息面/情绪面",
        "news_summary_heading": "新闻摘要",
        "market_sentiment_heading": "市场情绪",
        "hot_topics_heading": "相关热点",
        "analysis_heading": "综合分析",
        "search_performed_label": "已执行联网搜索",
        "data_sources_heading": "数据来源",
        "analysis_error_label": "分析异常",
        "market_review_title": "大盘复盘",
        "cn_market_review_title": "A股大盘复盘",
        "us_market_review_title": "美股大盘复盘",
        "stock_dashboard_merged_title": "个股决策仪表盘",
        "market_review_doc_title": "大盘复盘",
        "follow_up_us_market_review": "以下为美股大盘复盘",
        "market_summary_section": "市场总结",
        "index_commentary_section": "指数点评",
        "fund_flows_section": "资金动向",
        "sector_highlights_section": "热点解读",
        "outlook_section": "后市展望",
        "risk_alerts_section": "风险提示",
        "strategy_plan_section": "策略计划",
        "market_review_generated_at_label": "复盘时间",
        "market_stats_line": "上涨 {up} 家 / 下跌 {down} 家 / 平盘 {flat} 家 | 涨停 {limit_up} / 跌停 {limit_down} | 成交额 {amount:.0f} 亿",
        "leading_sectors_label": "领涨",
        "lagging_sectors_label": "领跌",
        "market_review_indices_header": "| 指数 | 最新 | 涨跌幅 | 成交额(亿) |",
    },
    "en": {
        "dashboard_title": "Decision Dashboard",
        "brief_title": "Decision Brief",
        "analyzed_prefix": "Analyzed",
        "stock_unit": "stocks",
        "stock_unit_compact": "stocks",
        "buy_label": "Buy",
        "watch_label": "Watch",
        "sell_label": "Sell",
        "summary_heading": "Summary",
        "info_heading": "Key Updates",
        "sentiment_summary_label": "Sentiment",
        "earnings_outlook_label": "Earnings Outlook",
        "risk_alerts_label": "Risk Alerts",
        "positive_catalysts_label": "Positive Catalysts",
        "latest_news_label": "Latest News",
        "core_conclusion_heading": "Core Conclusion",
        "one_sentence_label": "One-line Decision",
        "time_sensitivity_label": "Time Sensitivity",
        "default_time_sensitivity": "This week",
        "position_status_label": "Position",
        "action_advice_label": "Action",
        "no_position_label": "No Position",
        "has_position_label": "Holding",
        "continue_holding": "Continue holding",
        "market_snapshot_heading": "Market Snapshot",
        "close_label": "Close",
        "prev_close_label": "Prev Close",
        "open_label": "Open",
        "high_label": "High",
        "low_label": "Low",
        "change_pct_label": "Change %",
        "change_amount_label": "Change",
        "amplitude_label": "Amplitude",
        "volume_label": "Volume",
        "amount_label": "Turnover",
        "current_price_label": "Price",
        "volume_ratio_label": "Volume Ratio",
        "turnover_rate_label": "Turnover Rate",
        "source_label": "Source",
        "data_perspective_heading": "Data View",
        "ma_alignment_label": "MA Alignment",
        "bullish_alignment_label": "Bullish Alignment",
        "yes_label": "Yes",
        "no_label": "No",
        "trend_strength_label": "Trend Strength",
        "price_metrics_label": "Price Metrics",
        "ma5_label": "MA5",
        "ma10_label": "MA10",
        "ma20_label": "MA20",
        "bias_ma5_label": "Bias (MA5)",
        "support_level_label": "Support",
        "resistance_level_label": "Resistance",
        "chip_label": "Chip Structure",
        "battle_plan_heading": "Battle Plan",
        "ideal_buy_label": "Ideal Entry",
        "secondary_buy_label": "Secondary Entry",
        "stop_loss_label": "Stop Loss",
        "take_profit_label": "Target",
        "suggested_position_label": "Position Size",
        "entry_plan_label": "Entry Plan",
        "risk_control_label": "Risk Control",
        "checklist_heading": "Checklist",
        "failed_checks_heading": "Failed Checks",
        "history_compare_heading": "Historical Signal Comparison",
        "time_label": "Time",
        "score_label": "Score",
        "advice_label": "Advice",
        "trend_label": "Trend",
        "generated_at_label": "Generated At",
        "report_time_label": "Generated",
        "no_results": "No analysis results",
        "report_title": "Stock Analysis Report",
        "avg_score_label": "Avg Score",
        "action_points_heading": "Action Levels",
        "position_advice_heading": "Position Advice",
        "analysis_model_label": "Model",
        "not_investment_advice": "AI-generated content for reference only. Not investment advice.",
        "details_report_hint": "See detailed report:",
        "confidence_label": "Confidence",
        "key_points_label": "Key Points",
        "reason_label": "Rationale",
        "risk_warning_heading": "Risk Warning",
        "trend_analysis_heading": "Trend Analysis",
        "outlook_heading": "Outlook",
        "short_term_outlook_label": "Short Term (1-3 days)",
        "medium_term_outlook_label": "Medium Term (1-2 weeks)",
        "technical_heading": "Technicals",
        "technical_summary_label": "Overview",
        "ma_section_label": "Moving Averages",
        "volume_section_label": "Volume",
        "pattern_section_label": "Pattern",
        "fundamental_heading": "Fundamentals",
        "sector_position_label": "Sector Position",
        "company_highlights_label": "Company Highlights",
        "news_heading": "News Flow",
        "news_summary_heading": "News Summary",
        "market_sentiment_heading": "Market Sentiment",
        "hot_topics_heading": "Hot Topics",
        "analysis_heading": "Integrated Analysis",
        "search_performed_label": "Web search performed",
        "data_sources_heading": "Data Sources",
        "analysis_error_label": "Analysis Error",
        "market_review_title": "Market Review",
        "cn_market_review_title": "China Market Review",
        "us_market_review_title": "US Market Review",
        "stock_dashboard_merged_title": "Stock Decision Dashboard",
        "market_review_doc_title": "Market Review",
        "follow_up_us_market_review": "US market review follows below",
        "market_summary_section": "Market Summary",
        "index_commentary_section": "Index Commentary",
        "fund_flows_section": "Fund Flows",
        "sector_highlights_section": "Sector/Theme Highlights",
        "outlook_section": "Outlook",
        "risk_alerts_section": "Risk Alerts",
        "strategy_plan_section": "Strategy Plan",
        "market_review_generated_at_label": "Review Time",
        "market_stats_line": "Up {up} / Down {down} / Flat {flat} | Limit Up {limit_up} / Limit Down {limit_down} | Turnover {amount:.0f} bn CNY",
        "leading_sectors_label": "Leading",
        "lagging_sectors_label": "Lagging",
        "market_review_indices_header": "| Index | Last | Change % | Turnover (bn) |",
    },
}


def normalize_report_language(value: Optional[str], default: str = "zh") -> str:
    """Normalize report language to a supported short code."""
    candidate = (value or default).strip().lower().replace(" ", "_")
    candidate = _REPORT_LANGUAGE_ALIASES.get(candidate, candidate)
    if candidate in SUPPORTED_REPORT_LANGUAGES:
        return candidate
    return default


def normalize_log_language(value: Optional[str], default: str = "zh") -> str:
    """Normalize log language to zh/en/follow_report."""
    candidate = (value or default).strip().lower().replace(" ", "_")
    candidate = _LOG_LANGUAGE_ALIASES.get(candidate, candidate)
    if candidate in SUPPORTED_LOG_LANGUAGES:
        return candidate
    return default


def is_supported_report_language_value(value: Optional[str]) -> bool:
    """Return whether the raw value is a supported language code or alias."""
    candidate = (value or "").strip().lower().replace(" ", "_")
    if not candidate:
        return False
    return candidate in SUPPORTED_REPORT_LANGUAGES or candidate in _REPORT_LANGUAGE_ALIASES


def is_supported_log_language_value(value: Optional[str]) -> bool:
    """Return whether the raw value is a supported log language code or alias."""
    candidate = (value or "").strip().lower().replace(" ", "_")
    if not candidate:
        return False
    return candidate in SUPPORTED_LOG_LANGUAGES or candidate in _LOG_LANGUAGE_ALIASES


def resolve_log_language(
    log_language: Optional[str],
    report_language: Optional[str] = None,
) -> str:
    """Resolve effective log language after applying follow_report."""
    normalized = normalize_log_language(log_language, default="zh")
    if normalized == "follow_report":
        return normalize_report_language(report_language, default="zh")
    return normalized


def pick_localized_text(language: Optional[str], zh_text: str, en_text: str) -> str:
    """Return zh/en text pair based on normalized output language."""
    return en_text if normalize_report_language(language) == "en" else zh_text


def get_report_labels(language: Optional[str]) -> Dict[str, str]:
    """Return UI copy for the selected report language."""
    normalized = normalize_report_language(language)
    return _REPORT_LABELS[normalized]


def get_placeholder_text(language: Optional[str]) -> str:
    """Return placeholder text for missing localized content."""
    return _PLACEHOLDER_BY_LANGUAGE[normalize_report_language(language)]


def get_unknown_text(language: Optional[str]) -> str:
    """Return localized unknown text."""
    return _UNKNOWN_BY_LANGUAGE[normalize_report_language(language)]


def get_no_data_text(language: Optional[str]) -> str:
    """Return localized data unavailable text."""
    return _NO_DATA_BY_LANGUAGE[normalize_report_language(language)]


def contains_cjk_text(value: Any) -> bool:
    """Return whether a value contains any CJK characters."""
    return bool(_CJK_PATTERN.search(str(value or "")))


def _normalize_lookup_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", " ").replace("-", " ")


def _iter_lookup_candidates(value: Any) -> list[str]:
    raw_text = str(value or "").strip()
    if not raw_text:
        return []

    candidates = [raw_text]
    for part in re.split(r"[/|,，、]+", raw_text):
        normalized = part.strip()
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    return candidates


def _canonicalize_lookup_value(value: Any, canonical_map: Dict[str, str]) -> Optional[str]:
    for candidate in _iter_lookup_candidates(value):
        canonical = canonical_map.get(_normalize_lookup_key(candidate))
        if canonical:
            return canonical
    return None


def _is_placeholder_stock_name(value: Any, code: Any = None) -> bool:
    text = str(value or "").strip()
    if not text:
        return True

    lowered = text.lower()
    if lowered in {"n/a", "na", "none", "null", "unknown"}:
        return True
    if text in {"-", "—", "未知", "待补充"}:
        return True

    code_text = str(code or "").strip()
    if code_text and lowered == code_text.lower():
        return True

    return text.startswith("股票")


def _translate_from_map(
    value: Any,
    language: Optional[str],
    *,
    canonical_map: Dict[str, str],
    translations: Dict[str, Dict[str, str]],
) -> str:
    normalized_language = normalize_report_language(language)
    raw_text = str(value or "").strip()
    if not raw_text:
        return raw_text

    canonical = _canonicalize_lookup_value(raw_text, canonical_map)
    if canonical:
        return translations[canonical][normalized_language]
    return raw_text


def localize_operation_advice(value: Any, language: Optional[str]) -> str:
    """Translate operation advice between Chinese and English when recognized."""
    return _translate_from_map(
        value,
        language,
        canonical_map=_OPERATION_ADVICE_CANONICAL_MAP,
        translations=_OPERATION_ADVICE_TRANSLATIONS,
    )


def localize_trend_prediction(value: Any, language: Optional[str]) -> str:
    """Translate trend prediction between Chinese and English when recognized."""
    return _translate_from_map(
        value,
        language,
        canonical_map=_TREND_PREDICTION_CANONICAL_MAP,
        translations=_TREND_PREDICTION_TRANSLATIONS,
    )


def localize_confidence_level(value: Any, language: Optional[str]) -> str:
    """Translate confidence level between Chinese and English when recognized."""
    return _translate_from_map(
        value,
        language,
        canonical_map=_CONFIDENCE_LEVEL_CANONICAL_MAP,
        translations=_CONFIDENCE_LEVEL_TRANSLATIONS,
    )


def localize_chip_health(value: Any, language: Optional[str]) -> str:
    """Translate chip health labels between Chinese and English when recognized."""
    return _translate_from_map(
        value,
        language,
        canonical_map=_CHIP_HEALTH_CANONICAL_MAP,
        translations=_CHIP_HEALTH_TRANSLATIONS,
    )


def localize_bias_status(value: Any, language: Optional[str]) -> str:
    """Translate price bias status labels between Chinese and English when recognized."""
    return _translate_from_map(
        value,
        language,
        canonical_map=_BIAS_STATUS_CANONICAL_MAP,
        translations=_BIAS_STATUS_TRANSLATIONS,
    )


def get_bias_status_emoji(value: Any) -> str:
    """Return the stable alert emoji for a localized or canonical bias status."""
    canonical = _canonicalize_lookup_value(value, _BIAS_STATUS_CANONICAL_MAP)
    if canonical == "safe":
        return "✅"
    if canonical == "caution":
        return "⚠️"
    return "🚨"


def infer_decision_type_from_advice(value: Any, default: str = "hold") -> str:
    """Infer buy/hold/sell from human-readable operation advice."""
    canonical = _canonicalize_lookup_value(value, _OPERATION_ADVICE_CANONICAL_MAP)
    if canonical in {"strong_buy", "buy"}:
        return "buy"
    if canonical in {"reduce", "sell", "strong_sell"}:
        return "sell"
    if canonical in {"hold", "watch"}:
        return "hold"
    return default


def get_signal_level(advice: Any, score: Any, language: Optional[str]) -> tuple[str, str, str]:
    """Return localized signal text, emoji, and stable color tag."""
    normalized_language = normalize_report_language(language)
    canonical = _canonicalize_lookup_value(advice, _OPERATION_ADVICE_CANONICAL_MAP)
    if canonical == "strong_buy":
        return (_OPERATION_ADVICE_TRANSLATIONS["strong_buy"][normalized_language], "💚", "strong_buy")
    if canonical == "buy":
        return (_OPERATION_ADVICE_TRANSLATIONS["buy"][normalized_language], "🟢", "buy")
    if canonical == "hold":
        return (_OPERATION_ADVICE_TRANSLATIONS["hold"][normalized_language], "🟡", "hold")
    if canonical == "watch":
        return (_OPERATION_ADVICE_TRANSLATIONS["watch"][normalized_language], "⚪", "watch")
    if canonical == "reduce":
        return (_OPERATION_ADVICE_TRANSLATIONS["reduce"][normalized_language], "🟠", "reduce")
    if canonical in {"sell", "strong_sell"}:
        return (_OPERATION_ADVICE_TRANSLATIONS["sell"][normalized_language], "🔴", "sell")

    try:
        numeric_score = int(float(score))
    except (TypeError, ValueError):
        numeric_score = 50

    if numeric_score >= 80:
        return (_OPERATION_ADVICE_TRANSLATIONS["strong_buy"][normalized_language], "💚", "strong_buy")
    if numeric_score >= 65:
        return (_OPERATION_ADVICE_TRANSLATIONS["buy"][normalized_language], "🟢", "buy")
    if numeric_score >= 55:
        return (_OPERATION_ADVICE_TRANSLATIONS["hold"][normalized_language], "🟡", "hold")
    if numeric_score >= 45:
        return (_OPERATION_ADVICE_TRANSLATIONS["watch"][normalized_language], "⚪", "watch")
    if numeric_score >= 35:
        return (_OPERATION_ADVICE_TRANSLATIONS["reduce"][normalized_language], "🟠", "reduce")
    return (_OPERATION_ADVICE_TRANSLATIONS["sell"][normalized_language], "🔴", "sell")


def get_localized_stock_name(value: Any, code: Any, language: Optional[str]) -> str:
    """Return a localized stock name placeholder when the original name is missing."""
    raw_text = str(value or "").strip()
    normalized_language = normalize_report_language(language)
    if _is_placeholder_stock_name(raw_text, code):
        if normalized_language == "en":
            localized_name = _lookup_english_stock_name(raw_text, str(code or "").strip())
            if localized_name:
                return localized_name
        return _GENERIC_STOCK_NAME_BY_LANGUAGE[normalized_language]
    if normalized_language != "en":
        return raw_text
    if not contains_cjk_text(raw_text):
        return raw_text

    code_text = str(code or "").strip()
    localized_name = _lookup_english_stock_name(raw_text, code_text)
    return localized_name or raw_text


def get_sentiment_label(score: int, language: Optional[str]) -> str:
    """Return localized sentiment label by score band."""
    normalized = normalize_report_language(language)
    if normalized == "en":
        if score >= 80:
            return "Very Bullish"
        if score >= 60:
            return "Bullish"
        if score >= 40:
            return "Neutral"
        if score >= 20:
            return "Bearish"
        return "Very Bearish"

    if score >= 80:
        return "极度乐观"
    if score >= 60:
        return "乐观"
    if score >= 40:
        return "中性"
    if score >= 20:
        return "悲观"
    return "极度悲观"


def localize_market_term(value: Any, language: Optional[str]) -> str:
    """Return curated English aliases for major CN market terms with fallback."""
    normalized_language = normalize_report_language(language)
    raw_text = str(value or "").strip()
    if not raw_text or normalized_language != "en":
        return raw_text
    if not contains_cjk_text(raw_text):
        return raw_text

    alias = _CN_MARKET_TERM_ALIASES.get(raw_text)
    if alias:
        return alias

    if raw_text not in _MISSING_MARKET_TERM_WARNINGS:
        logger.warning("Missing English alias for market term: %s", raw_text)
        _MISSING_MARKET_TERM_WARNINGS.add(raw_text)
    return raw_text


def _stock_code_candidates(code: Any) -> list[str]:
    raw_code = str(code or "").strip()
    if not raw_code:
        return []

    upper_code = raw_code.upper()
    candidates = [upper_code]
    stripped = upper_code
    if stripped.startswith("HK") and len(stripped) > 2:
        stripped = stripped[2:]
        if stripped not in candidates:
            candidates.append(stripped)
    if "." in upper_code:
        base = upper_code.split(".", 1)[0]
        if base not in candidates:
            candidates.append(base)
    if raw_code not in candidates:
        candidates.append(raw_code)
    return candidates


def _looks_like_english_name(value: str) -> bool:
    if not value:
        return False
    if contains_cjk_text(value):
        return False
    letters = re.findall(r"[A-Za-z]", value)
    return bool(letters)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def _load_csv_english_name_mappings() -> Dict[str, str]:
    mappings: Dict[str, str] = {}
    data_dir = _project_root() / "data"
    for filename in ("stock_list_a.csv", "stock_list_hk.csv", "stock_list_us.csv"):
        csv_path = data_dir / filename
        if not csv_path.exists():
            continue
        try:
            with open(csv_path, "r", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    row_name = str(row.get("name") or "").strip()
                    row_enname = str(row.get("enname") or "").strip()
                    ts_code = str(row.get("ts_code") or "").strip()
                    symbol = str(row.get("symbol") or "").strip()
                    if not row_enname or not _looks_like_english_name(row_enname):
                        continue

                    for candidate in _stock_code_candidates(ts_code) + _stock_code_candidates(symbol):
                        mappings[candidate] = row_enname
                    if row_name and row_name not in mappings:
                        mappings[row_name] = row_enname
        except Exception as exc:  # pragma: no cover - defensive path
            logger.debug("Failed to load stock name aliases from %s: %s", csv_path, exc)
    return mappings


@lru_cache(maxsize=1)
def _load_index_english_name_mappings() -> Dict[str, str]:
    mappings: Dict[str, str] = {}
    index_path = _project_root() / "apps" / "dsa-web" / "public" / "stocks.index.json"
    if not index_path.exists():
        return mappings

    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive path
        logger.debug("Failed to load stock index aliases from %s: %s", index_path, exc)
        return mappings

    for item in data:
        if not isinstance(item, list) or len(item) < 6:
            continue
        canonical_code = str(item[0] or "").strip()
        display_code = str(item[1] or "").strip()
        primary_name = str(item[2] or "").strip()
        aliases = item[5] if isinstance(item[5], list) else []

        english_aliases = [
            str(alias).strip()
            for alias in aliases
            if isinstance(alias, str) and _looks_like_english_name(alias) and not re.fullmatch(r"[A-Z0-9.]+", alias.strip())
        ]
        preferred = english_aliases[0] if english_aliases else (primary_name if _looks_like_english_name(primary_name) else "")
        if not preferred:
            continue

        for candidate in _stock_code_candidates(canonical_code) + _stock_code_candidates(display_code):
            mappings[candidate] = preferred
        if primary_name and primary_name not in mappings:
            mappings[primary_name] = preferred

    return mappings


def _lookup_english_stock_name(name: str, code: str) -> str:
    for candidate in _stock_code_candidates(code):
        if candidate in _ENGLISH_STOCK_NAME_BY_CODE:
            return _ENGLISH_STOCK_NAME_BY_CODE[candidate]
    if name in _ENGLISH_STOCK_NAME_BY_NAME:
        return _ENGLISH_STOCK_NAME_BY_NAME[name]

    csv_mappings = _load_csv_english_name_mappings()
    for candidate in _stock_code_candidates(code):
        if candidate in csv_mappings:
            return csv_mappings[candidate]
    if name in csv_mappings:
        return csv_mappings[name]

    index_mappings = _load_index_english_name_mappings()
    for candidate in _stock_code_candidates(code):
        if candidate in index_mappings:
            return index_mappings[candidate]
    return index_mappings.get(name, "")
