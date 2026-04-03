#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare Stock List Fetch Script

Fetch A-share, Hong Kong, and US stock lists from Tushare Pro and save them as CSV files.

Usage:
    python3 scripts/fetch_tushare_stock_list.py

Requirements:
    - Set TUSHARE_TOKEN in .env
    - Install tushare: pip install tushare
    - Account points required:
        * A-shares / HK stocks: 2000 points
        * US stocks: 120 points for trial access, 5000 for full access

Output files:
    - data/stock_list_a.csv      A-share list
    - data/stock_list_hk.csv     Hong Kong stock list
    - data/stock_list_us.csv     US stock list
    - data/README_stock_list.md  Data documentation
"""

import os
import sys
import time
import random
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd
from dotenv import load_dotenv

# Add the project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import tushare as ts
except ImportError:
    print("[ERROR] tushare is not installed")
    print("Run: pip install tushare")
    sys.exit(1)


# Config
load_dotenv()

TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN')
OUTPUT_DIR = Path(__file__).parent.parent / "data"
PAGE_SIZE = 5000  # Rows per US-stock page (API max is 6000; keep headroom at 5000)
SLEEP_MIN = 5     # Minimum sleep time in seconds
SLEEP_MAX = 10    # Maximum sleep time in seconds


def get_tushare_api() -> Optional[ts.pro_api]:
    """
    Get a Tushare API client.

    Returns:
        Tushare API client, or None on failure
    """
    if not TUSHARE_TOKEN:
        print("[ERROR] TUSHARE_TOKEN was not found")
        print("Set it in .env, for example: TUSHARE_TOKEN=your_token")
        return None

    try:
        api = ts.pro_api(TUSHARE_TOKEN)
        # Smoke-test the connection
        api.trade_cal(exchange='SSE', start_date='20240101', end_date='20240101')
        print("✓ Tushare API connection succeeded")
        return api
    except Exception as e:
        print(f"[ERROR] Tushare API connection failed: {e}")
        print("Check the following:")
        print("  1. TUSHARE_TOKEN is correct")
        print("  2. Your account has enough points (A-shares / HK stocks require 2000 points)")
        return None


def random_sleep(min_seconds: int = SLEEP_MIN, max_seconds: int = SLEEP_MAX):
    """
    Sleep for a random interval to avoid sending requests too frequently.

    Args:
        min_seconds: Minimum sleep time
        max_seconds: Maximum sleep time
    """
    sleep_time = random.uniform(min_seconds, max_seconds)
    print(f"  ⏱  Sleeping for {sleep_time:.1f} seconds...")
    time.sleep(sleep_time)


def fetch_a_stock_list(api: ts.pro_api) -> Optional[pd.DataFrame]:
    """
    Fetch the A-share stock list.

    API: stock_basic
    Limit: up to 6000 rows per call, enough to cover the full A-share market

    Args:
        api: Tushare API client

    Returns:
        A-share DataFrame, or None on failure
    """
    print("\n[1/3] Fetching A-share stock list...")

    try:
        # Fetch all normally listed stocks
        df = api.stock_basic(
            exchange='',        # Empty means all exchanges
            list_status='L',    # L: listed, D: delisted, P: suspended
            fields='ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type'
        )

        if df is not None and len(df) > 0:
            print(f"✓ A-share stock list fetched successfully: {len(df)} stocks")
            print("  - Exchange distribution:")
            for exchange, count in df['exchange'].value_counts().items():
                print(f"    {exchange}: {count} stocks")
            return df
        else:
            print("[ERROR] A-share dataset is empty")
            return None

    except Exception as e:
        print(f"[ERROR] Failed to fetch A-share stock list: {e}")
        return None


def fetch_hk_stock_list(api: ts.pro_api) -> Optional[pd.DataFrame]:
    """
    Fetch the Hong Kong stock list.

    API: hk_basic
    Limit: one call can fetch the full actively traded Hong Kong stock list

    Args:
        api: Tushare API client

    Returns:
        Hong Kong stock DataFrame, or None on failure
    """
    print("\n[2/3] Fetching Hong Kong stock list...")

    try:
        # Fetch all normally listed Hong Kong stocks
        df = api.hk_basic(
            list_status='L'    # L: listed, D: delisted
        )

        if df is not None and len(df) > 0:
            print(f"✓ Hong Kong stock list fetched successfully: {len(df)} stocks")
            return df
        else:
            print("[ERROR] Hong Kong stock dataset is empty")
            return None

    except Exception as e:
        print(f"[ERROR] Failed to fetch Hong Kong stock list: {e}")
        return None


def fetch_us_stock_list(api: ts.pro_api) -> Optional[pd.DataFrame]:
    """
    Fetch the US stock list with pagination.

    API: us_basic
    Limit: up to 6000 rows per call, so pagination is required

    Args:
        api: Tushare API client

    Returns:
        US stock DataFrame, or None on failure
    """
    print("\n[3/3] Fetching US stock list with pagination...")

    all_data = []
    offset = 0
    page = 1

    try:
        while True:
            print(f"  Page {page} (offset={offset})...")

            df = api.us_basic(
                offset=offset,
                limit=PAGE_SIZE
            )

            if df is None or len(df) == 0:
                print(f"  ✓ Page {page} returned no data; fetch complete")
                break

            all_data.append(df)
            print(f"  ✓ Page {page} fetched {len(df)} stocks")

            # Fewer rows than PAGE_SIZE means this is the final page
            if len(df) < PAGE_SIZE:
                break

            offset += PAGE_SIZE
            page += 1

            # Random sleep between pages; no sleep needed after the last page
            random_sleep()

        if all_data:
            result_df = pd.concat(all_data, ignore_index=True)
            print(f"✓ US stock list fetched successfully: {len(result_df)} stocks across {page} page(s)")

            # Print classification stats
            if 'classify' in result_df.columns:
                print("  - Classification distribution:")
                for classify, count in result_df['classify'].value_counts().items():
                    print(f"    {classify}: {count} stocks")

            return result_df
        else:
            print("[ERROR] US stock dataset is empty")
            return None

    except Exception as e:
        print(f"[ERROR] Failed to fetch US stock list: {e}")
        return None


def save_to_csv(df: pd.DataFrame, filename: str, market_name: str) -> bool:
    """
    Save data to a CSV file.

    Args:
        df: DataFrame to save
        filename: Output file name
        market_name: Market label used in logs

    Returns:
        Whether the save succeeded
    """
    if df is None or len(df) == 0:
        print(f"[SKIP] {market_name} data is empty; file will not be written")
        return False

    try:
        output_path = OUTPUT_DIR / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df.to_csv(output_path, index=False, encoding='utf-8-sig')

        file_size = output_path.stat().st_size / 1024  # KB
        print(f"✓ Saved {market_name} data: {output_path} ({file_size:.2f} KB)")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to save {market_name} data: {e}")
        return False


def generate_data_documentation(
    a_df: Optional[pd.DataFrame],
    hk_df: Optional[pd.DataFrame],
    us_df: Optional[pd.DataFrame]
):
    """
    Generate the stock-list documentation file.

    Args:
        a_df: A-share data
        hk_df: Hong Kong stock data
        us_df: US stock data
    """
    doc_path = OUTPUT_DIR / "README_stock_list.md"

    content = f"""# Tushare 股票列表数据说明

> 数据来源：[Tushare Pro](https://tushare.pro)
> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 文件说明

| 文件 | 说明 | 记录数 |
|------|------|--------|
| `stock_list_a.csv` | A股列表 | {len(a_df) if a_df is not None else 0} |
| `stock_list_hk.csv` | 港股列表 | {len(hk_df) if hk_df is not None else 0} |
| `stock_list_us.csv` | 美股列表 | {len(us_df) if us_df is not None else 0} |

---

## A股数据（stock_list_a.csv）

### 数据接口
- **接口名称**：`stock_basic`
- **数据权限**：2000积分起，每分钟请求50次
- **数据限量**：单次最多6000行（覆盖全市场A股）

### 字段说明

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| ts_code | str | TS代码 | 000001.SZ |
| symbol | str | 股票代码 | 000001 |
| name | str | 股票名称 | 平安银行 |
| area | str | 地域 | 深圳 |
| industry | str | 所属行业 | 银行 |
| fullname | str | 股票全称 | 平安银行股份有限公司 |
| enname | str | 英文全称 | Ping An Bank Co., Ltd. |
| cnspell | str | 拼音缩写 | PAYH |
| market | str | 市场类型 | 主板/创业板/科创板/CDR |
| exchange | str | 交易所代码 | SSE上交所/SZSE深交所/BSE北交所 |
| curr_type | str | 交易货币 | CNY |
| list_status | str | 上市状态 | L上市/D退市/P暂停上市 |
| list_date | str | 上市日期 | 19910403 |
| delist_date | str | 退市日期 | - |
| is_hs | str | 是否沪深港通标的 | N否/H沪股通/S深股通 |
| act_name | str | 实控人名称 | - |
| act_ent_type | str | 实控人企业性质 | - |

### 数据样例
```csv
ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type
000001.SZ,000001,平安银行,深圳,银行,平安银行股份有限公司,Ping An Bank Co., Ltd.,PAYH,主板,SZSE,CNY,L,19910403,,S,,
000002.SZ,000002,万科A,深圳,全国地产,万科企业股份有限公司,China Vanke Co., Ltd.,ZKA,主板,SZSE,CNY,L,19910129,,S,,
```

---

## 港股数据（stock_list_hk.csv）

### 数据接口
- **接口名称**：`hk_basic`
- **数据权限**：用户需要至少2000积分才可以调取
- **数据限量**：单次可提取全部在交易的港股列表数据

### 字段说明

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| ts_code | str | TS代码 | 00001.HK |
| name | str | 股票简称 | 长和 |
| fullname | str | 公司全称 | 长江和记实业有限公司 |
| enname | str | 英文名称 | CK Hutchison Holdings Ltd. |
| cn_spell | str | 拼音 | ZH |
| market | str | 市场类别 | 主板/创业板 |
| list_status | str | 上市状态 | L上市/D退市/P暂停上市 |
| list_date | str | 上市日期 | 19720731 |
| delist_date | str | 退市日期 | - |
| trade_unit | float | 交易单位 | 1000 |
| isin | str | ISIN代码 | KYG217651051 |
| curr_type | str | 货币代码 | HKD |

### 数据样例
```csv
ts_code,name,fullname,enname,cn_spell,market,list_status,list_date,delist_date,trade_unit,isin,curr_type
00001.HK,长和,长江和记实业有限公司,CK Hutchison Holdings Ltd.,ZH,主板,L,19720731,,1000,KYG217651051,HKD
00002.HK,中电控股,中华电力有限公司,CLP Holdings Ltd.,ZDKG,主板,L,19860125,,1000,HK0002007356,HKD
```

---

## 美股数据（stock_list_us.csv）

### 数据接口
- **接口名称**：`us_basic`
- **数据权限**：120积分可以试用，5000积分有正式权限
- **数据限量**：单次最大6000，可分页提取

### 字段说明

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| ts_code | str | 美股代码 | AAPL |
| name | str | 中文名称 | 苹果 |
| enname | str | 英文名称 | Apple Inc. |
| classify | str | 分类 | ADR/GDR/EQT |
| list_date | str | 上市日期 | 19801212 |
| delist_date | str | 退市日期 | - |

### 分类说明
- **ADR**：美国存托凭证（American Depositary Receipt）
- **GDR**：全球存托凭证（Global Depositary Receipt）
- **EQT**：普通股（Equity）

### 数据样例
```csv
ts_code,name,enname,classify,list_date,delist_date
AAPL,苹果,Apple Inc.,EQT,19801212,
TSLA,特斯拉,Tesla Inc.,EQT,20100629,
BABA,阿里巴巴,Alibaba Group Holding Ltd.,ADR,20140919,
```

---

## 使用说明

### 读取数据

```python
import pandas as pd

# 读取 A股数据
a_stocks = pd.read_csv('data/stock_list_a.csv')

# 读取港股数据
hk_stocks = pd.read_csv('data/stock_list_hk.csv')

# 读取美股数据
us_stocks = pd.read_csv('data/stock_list_us.csv')
```

### 代码格式说明

**A股代码格式**：
- 沪市：`600000.SH`（主板）、`688xxx.SH`（科创板）、`900xxx.SH`（B股）
- 深市：`000001.SZ`（主板）、`300xxx.SZ`（创业板）、`200xxx.SZ`（B股）
- 北交所：`8xxxxx.BJ`、`4xxxxx.BJ`、`920xxx.BJ`

**港股代码格式**：
- 格式：`xxxxx.HK`（5位数字 + .HK）
- 示例：`00700.HK`（腾讯控股）

**美股代码格式**：
- 格式：代码字母（无后缀）
- 示例：`AAPL`（苹果）、`TSLA`（特斯拉）

---

## 注意事项

1. **数据更新**：建议定期更新数据（如每月一次）
2. **积分要求**：
   - A股/港股：需要2000积分
   - 美股：120积分试用，5000积分正式权限
3. **请求限制**：注意 API 的每分钟请求次数限制
4. **数据完整性**：本数据仅包含基础信息，如需更多数据请参考 Tushare 官方文档

---

## 相关链接

- [Tushare 官网](https://tushare.pro)
- [Tushare 文档](https://tushare.pro/document/2)
- [积分获取办法](https://tushare.pro/document/1)
- [API 数据调试](https://tushare.pro/document/2)
"""

    try:
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Data documentation generated: {doc_path}")
    except Exception as e:
        print(f"[ERROR] Failed to generate documentation: {e}")


def main():
    """Main entrypoint."""
    print("=" * 60)
    print("Tushare Stock List Fetch Tool")
    print("=" * 60)

    # 1. Get the API client
    api = get_tushare_api()
    if not api:
        return 1

    # 2. Fetch A-share data
    a_df = fetch_a_stock_list(api)
    if a_df is not None:
        save_to_csv(a_df, 'stock_list_a.csv', 'A-shares')

    # 3. Fetch Hong Kong stock data
    random_sleep()  # Pause before the next market
    hk_df = fetch_hk_stock_list(api)
    if hk_df is not None:
        save_to_csv(hk_df, 'stock_list_hk.csv', 'Hong Kong stocks')

    # 4. Fetch US stock data with pagination
    random_sleep()  # Pause before the next market
    us_df = fetch_us_stock_list(api)
    if us_df is not None:
        save_to_csv(us_df, 'stock_list_us.csv', 'US stocks')

    # 5. Generate documentation
    print("\nGenerating data documentation...")
    generate_data_documentation(a_df, hk_df, us_df)

    # 6. Summary
    print("\n" + "=" * 60)
    print("Done.")
    print("=" * 60)

    total_count = 0
    if a_df is not None:
        total_count += len(a_df)
        print(f"  ✓ A-shares: {len(a_df)} stocks")
    if hk_df is not None:
        total_count += len(hk_df)
        print(f"  ✓ Hong Kong stocks: {len(hk_df)} stocks")
    if us_df is not None:
        total_count += len(us_df)
        print(f"  ✓ US stocks: {len(us_df)} stocks")

    print(f"\nTotal: {total_count} stocks")
    print(f"Output directory: {OUTPUT_DIR}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
