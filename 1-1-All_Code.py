import akshare as ak
import pandas as pd
import datetime
import os

# ===============================
# 1. 获取所有 A 股代码 + 名称
# ===============================
def get_all_a_symbols():
    stock_df = ak.stock_info_a_code_name()
    return stock_df

# 获取数据
stock_df = get_all_a_symbols()
print(f"✅ 共获取到 {len(stock_df)} 支股票代码")

# ===============================
# 2. 保存成 CSV 文件
# ===============================
today = datetime.date.today().strftime("%Y%m%d")
filename = f"Ashare_codes_{today}.csv"
os.makedirs("data", exist_ok=True)
save_path = os.path.join("data", filename)

stock_df.to_csv(save_path, index=False, encoding="utf-8-sig")
print(f"📄 已保存至 {save_path}")
