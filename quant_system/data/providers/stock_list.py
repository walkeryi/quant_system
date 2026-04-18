# -*- coding: utf-8 -*-
"""
股票列表数据获取
"""
import requests
import pandas as pd
from quant_system.common.storage import Storage
from quant_system.common import db_manager
from quant_system.config import HSA_TOKEN, STOCK_LIST_CACHE
from datetime import datetime


class StockListProvider:
    """获取股票列表数据"""
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
                return self._fill_market_data(df), data.get('ver', "")
        except Exception as e:
            print(f"Fetch stock list error: {e}")
            return None, None

    def _fill_market_data(self, df):
        """
        行情填充：列表页的行情先用0填充，真实行情在个股详情页获取
        """
        if df is None or df.empty:
            return df
        if 'price' not in df.columns:
            df['price'] = 0.0
            df['pct_chg'] = 0.0
            df['high'] = 0.0
            df['low'] = 0.0
            df['volume'] = 0
        return df
