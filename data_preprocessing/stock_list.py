import requests
import pandas as pd
from common.storage import Storage
from config import HSA_TOKEN, STOCK_LIST_CACHE

class StockListProvider:
    """获取股票列表逻辑"""
    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_gupiao"

    def fetch(self, use_cache=True):
        if use_cache:
            df = Storage.load_csv(STOCK_LIST_CACHE)
            if df is not None: return df, "Cache"

        try:
            resp = requests.get(self.API_URL, params={'token': HSA_TOKEN}, timeout=10)
            data = resp.json()
            if data.get('ret') == 200:
                df = pd.DataFrame(data.get('data', []))
                Storage.save_csv(df, STOCK_LIST_CACHE)
                return df, data.get('ver', "")
        except: return None, None