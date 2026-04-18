# -*- coding: utf-8 -*-
"""
分时数据获取
"""
import requests
import pandas as pd
from quant_system.config import HSA_TOKEN
from quant_system.common.utils import log_exceptions, setup_logger

logger = setup_logger(__name__)


class FenshiDataProvider:
    """获取分时数据"""
    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_fenshi"

    @log_exceptions(logger)
    def fetch(self, code: str, fetch_all: bool = True):
        """
        :param code: 股票代码
        :param fetch_all: True=获取全天数据，False=增量获取
        """
        code = str(code).zfill(6)
        params = {
            'token': HSA_TOKEN,
            'code': code,
            'all': 1 if fetch_all else 0
        }
        resp = requests.get(self.API_URL, params=params, timeout=15)
        data = resp.json()
        logger.info(f"[Provider] code={code} fetch_all={fetch_all} ret={data.get('ret')} data_count={len(data.get('data', []))}")
        if data.get('ret') != 200:
            raise ValueError(f"API错误: {data.get('msg', '未知')}")

        base = data.get('base', {})
        items = data.get('data', [])
        if not items:
            return pd.DataFrame()

        df = pd.DataFrame(items)
        col_mapping = {
            'JiaGe': 'price',
            'ShiJian': 'time',
            'JunJia': 'avg_price',
            'ZongLiang': 'minute_volume',
            'ZhangFu': 'pct_chg',
            'HuanShou': 'huan_shou',
            'LiangBi': 'liang_bi',
            'WeiBi': 'wei_bi',
            'NeiPan': 'nei_pan',
            'WaiPan': 'wai_pan',
            'JinE': 'amount',
            'ZhangSu': 'zhang_su',
        }
        df.rename(columns=col_mapping, inplace=True)
        if 'time' in df.columns:
            df['time'] = df['time'].astype(str)
        if 'price' in df.columns:
            df['price'] = df['price'].astype(float) / 1000.0
        if 'avg_price' in df.columns:
            df['avg_price'] = df['avg_price'].astype(float) / 1000.0
        if 'minute_volume' in df.columns:
            df['minute_volume'] = df['minute_volume'].astype(float)
        if 'pct_chg' in df.columns:
            df['pct_chg'] = df['pct_chg'].astype(float) / 100.0

        df.attrs['base'] = base
        df.attrs['ret'] = 200
        logger.info(f"[Provider] code={code} df.columns={list(df.columns)} rows={len(df)} base_keys={list(base.keys())}")
        return df

    def save_to_db(self, df: pd.DataFrame) -> int:
        """保存分时数据到数据库"""
        from quant_system.common import db_manager
        base = df.attrs.get('base', {})
        code = base.get('code')
        trade_date = base.get('date')
        if not code or not trade_date:
            return 0
        records = []
        for _, row in df.iterrows():
            time_str = str(row.get('time', '')).strip()
            if len(time_str) == 5:
                time_str += ":00"
            price_val = float(row.get('price', 0))
            volume_val = int(row.get('minute_volume', 0))
            amount_val = price_val * volume_val * 100
            records.append((code, trade_date, time_str, price_val, volume_val, amount_val))
        return len(records)
