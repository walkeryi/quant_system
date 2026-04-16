import requests
import pandas as pd
import numpy as np  # 👇 新增：用于生成随机模拟数据
from common.storage import Storage
from common import db_manager
from config import HSA_TOKEN, STOCK_LIST_CACHE
from datetime import datetime


class StockListProvider:
    """获取股票列表逻辑"""
    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_gupiao"

    def fetch(self, use_cache=True):
        db_manager.init_db()
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        latest_day = db_manager.get_latest_update_date()

        if use_cache and latest_day == today:
            db_df = db_manager.load_stock_list_df()
            if db_df is not None and not db_df.empty:
                return self._fill_market_data(db_df), "SQLite"

        if use_cache and latest_day == today:
            df = Storage.load_parquet(STOCK_LIST_CACHE)
            if df is not None:
                return self._fill_market_data(df), "Cache"

        if now.hour < 10:
            db_df = db_manager.load_stock_list_df()
            if db_df is not None and not db_df.empty:
                return self._fill_market_data(db_df), "SQLite-Pre10"

        try:
            resp = requests.get(self.API_URL, params={'token': HSA_TOKEN}, timeout=10)
            data = resp.json()
            if data.get('ret') == 200:
                df = pd.DataFrame(data.get('data', []))
                Storage.save_parquet(df, STOCK_LIST_CACHE)
                db_manager.bulk_upsert_from_df(self._fill_market_data(df.copy()))
                # 👇 返回前，为其填充模拟的行情数据
                return self._fill_market_data(df), data.get('ver', "")
        except Exception as e:
            print(f"Fetch stock list error: {e}")
            return None, None

    def _fill_market_data(self, df):
        """
        移除随机假数据逻辑：
        因为 hsa_gupiao 接口没有行情，而 hsa_fenshi 接口一次只能查单只股票，
        为了防止列表加载时发起 5000 次请求导致卡死/封号，
        这里列表页的行情先用 0 填充。真实行情将在双击进入个股详情页时获取。
        """
        if df is None or df.empty:
            return df

        # 如果数据中没有最新价，用 0 填充，而不是使用随机数造假
        if 'price' not in df.columns:
            df['price'] = 0.0
            df['pct_chg'] = 0.0
            df['high'] = 0.0
            df['low'] = 0.0
            df['volume'] = 0

        return df