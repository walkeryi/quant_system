# -*- coding: utf-8 -*-
"""
月线数据获取
"""
import requests
import pandas as pd
from quant_system.config import HSA_TOKEN
from quant_system.common.utils import log_exceptions, setup_logger

logger = setup_logger(__name__)


class MonthlyDataProvider:
    """获取月线数据"""
    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_yuexiandata"

    @log_exceptions(logger)
    def fetch(self, code: str):
        code = str(code).zfill(6)
        params = {'token': HSA_TOKEN, 'code': code}
        resp = requests.get(self.API_URL, params=params, timeout=15)
        data = resp.json()
        if data.get('ret') != 200:
            raise ValueError(f"API错误: {data.get('msg', '未知')}")

        items = data.get('data', [])
        if not items:
            return pd.DataFrame()
        df = pd.DataFrame(items)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.attrs['ret'] = 200
        df.attrs['base'] = {'code': code}
        return df
