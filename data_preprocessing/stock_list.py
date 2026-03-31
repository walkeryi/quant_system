import requests
import pandas as pd
import numpy as np  # 👇 新增：用于生成随机模拟数据
from common.storage import Storage
from config import HSA_TOKEN, STOCK_LIST_CACHE


class StockListProvider:
    """获取股票列表逻辑"""
    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_gupiao"

    def fetch(self, use_cache=True):
        if use_cache:
            df = Storage.load_parquet(STOCK_LIST_CACHE)
            if df is not None:
                # 👇 返回前，为其填充模拟的行情数据
                return self._fill_market_data(df), "Cache"

        try:
            resp = requests.get(self.API_URL, params={'token': HSA_TOKEN}, timeout=10)
            data = resp.json()
            if data.get('ret') == 200:
                df = pd.DataFrame(data.get('data', []))
                Storage.save_parquet(df, STOCK_LIST_CACHE)
                # 👇 返回前，为其填充模拟的行情数据
                return self._fill_market_data(df), data.get('ver', "")
        except Exception as e:
            print(f"Fetch stock list error: {e}")
            return None, None

    def _fill_market_data(self, df):
        """
        数据填充逻辑：
        因为 hsa_gupiao 接口没有返回价格和涨跌幅，在这里临时生成模拟数据。
        后续如果有【批量行情API】，可以在这里进行真实数据的合并(Merge)操作。
        """
        if df is None or df.empty:
            return df

        # 如果数据中没有最新价，说明是纯净的列表，进行模拟填充
        if 'price' not in df.columns:
            # 1. 模拟最新价：5.00 ~ 100.00 之间
            df['price'] = np.round(np.random.uniform(5.0, 100.0, size=len(df)), 2)

            # 2. 模拟涨跌幅：-10.00% ~ +10.00% 之间
            df['pct_chg'] = np.round(np.random.uniform(-10.0, 10.0, size=len(df)), 2)

            # 3. 模拟最高价和最低价
            df['high'] = np.round(df['price'] * np.random.uniform(1.0, 1.05, size=len(df)), 2)
            df['low'] = np.round(df['price'] * np.random.uniform(0.95, 1.0, size=len(df)), 2)

            # 4. 模拟成交量：1万手 ~ 100万手之间
            df['volume'] = np.random.randint(10000, 1000000, size=len(df))

        return df