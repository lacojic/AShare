import akshare as ak
import pandas as pd
import os
import time
import datetime

# ===============================
# 1. 基本配置
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# 新增子文件夹 each_code_k_data
CODE_DATA_DIR = os.path.join(DATA_DIR, "each_code_k_data")
os.makedirs(CODE_DATA_DIR, exist_ok=True)

CODES_FILE = os.path.join(DATA_DIR, "Ashare_codes_all.csv")

# ===============================
# 2. 从文件读取股票代码（保留前导0）
# ===============================
if not os.path.exists(CODES_FILE):
    raise FileNotFoundError(f"未找到股票代码文件：{CODES_FILE}")

codes_df = pd.read_csv(CODES_FILE, dtype={"code": str})
codes = codes_df["code"].tolist()
print(f"✅ 共读取 {len(codes)} 支股票代码")

# ===============================
# 3. 定义获取 K 线函数（无重试）
# ===============================
def get_kline_data(symbol: str):
    """获取单只股票日线数据（前复权），返回 DataFrame 或 None"""
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
        df = df.rename(columns={
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume"
        })
        df = df[["date", "open", "high", "low", "close", "volume"]]
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        return df
    except Exception as e:
        print(f"⚠️ {symbol} 下载失败: {e}")
        return None

# ===============================
# 4. 批量下载（无重试）+ 每次打印总进度
# ===============================
success_count = 0
fail_count = 0
skip_count = 0

total = len(codes)

for i, code in enumerate(codes, 1):

    # 判断是否已有文件
    existing_files = [f for f in os.listdir(CODE_DATA_DIR) if f.startswith(f"Ashare_{code}_")]
    if existing_files:
        skip_count += 1
        print(f"({i}/{total}) ⏩ 跳过 {code}（文件已存在）")
    else:
        # 无重试：直接请求一次
        df = get_kline_data(code)

        # 判断是否成功
        if df is None or df.empty:
            fail_count += 1
            print(f"({i}/{total}) ❌ {code} 无数据或下载失败")
        else:
            # 构造文件名并保存
            start_date = df["date"].iloc[0].strftime("%Y%m%d")
            row_count = len(df)
            filename = f"Ashare_{code}_{row_count}_{start_date}.csv"
            filepath = os.path.join(CODE_DATA_DIR, filename)
            df.to_csv(filepath, index=False, encoding="utf-8-sig")

            success_count += 1
            print(f"({i}/{total}) ✅ 保存 {filename}")

    # 🔥 每只股票结束后打印总进度
    print(f"— 当前统计：成功 {success_count} | 失败 {fail_count} | 跳过 {skip_count}\n")

# ===============================
# 5. 最终统计汇总
# ===============================
print("\n🎯 全部股票数据获取完成！")
print(f"✅ 新获取成功: {success_count} 支股票")
print(f"⚠️ 下载失败: {fail_count} 支股票")
print(f"⏩ 已存在跳过: {skip_count} 支股票")
print("📊 下载结束时间：", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
