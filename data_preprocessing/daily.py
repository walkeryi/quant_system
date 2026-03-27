# quant_system/data_preprocessing/daily.py
import requests
import pandas as pd
from common.utils import setup_logger, log_exceptions
from config import HSA_TOKEN

logger = setup_logger(__name__)


class DailyDataProvider:
    """获取沪深个股日线数据"""
    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_rixian"

    def __init__(self, token: str = HSA_TOKEN):
        self.token = token

    @log_exceptions(logger)
    def fetch(self, code: str, all_data: bool = False) -> pd.DataFrame | None:
        params = {
            'token': self.token,
            'code': code,
            'all': 1 if all_data else 0  # 核心：看盘传0(100笔)，回测传1(全部)
        }
        try:
            log_msg = "全部数据" if all_data else "最新100笔"
            logger.info(f"正在向日线 API 请求数据: code={code}, 范围={log_msg}")

            resp = requests.get(self.API_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get('ret') != 200:
                return None

            base = data.get('base', {})
            records = data.get('data', [])
            if not records:
                return pd.DataFrame()

            df = pd.DataFrame(records)

            # 映射中文拼音列名到标准英文
            column_map = {
                'RiQi': 'date', 'KaiPan': 'open', 'ZuiGao': 'high',
                'ZuiDi': 'low', 'ShouPan': 'close', 'ZongLiang': 'volume',
                'JinE': 'amount', 'HuanShou': 'turnover', 'ZhangFu': 'pct_chg',
                'ZhangSu': 'speed', 'LiangBi': 'vol_ratio', 'WeiBi': 'wei_ratio',
                'NeiPan': 'inner_vol', 'WaiPan': 'outer_vol'
            }
            df.rename(columns=lambda x: column_map.get(x, x), inplace=True)

            # 价格单位转换 (0.1分 -> 元)
            price_cols = ['open', 'high', 'low', 'close', 'JunJia']
            for col in price_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce') / 1000.0

            # 比例单位转换 (0.001% -> %)
            pct_cols = ['turnover', 'pct_chg', 'speed', 'vol_ratio', 'wei_ratio']
            for col in pct_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce') / 1000.0

            if 'volume' in df.columns:
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            if 'amount' in df.columns:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)

            df.attrs['base'] = {
                'name': base.get('name', ''),
                'code': base.get('code', code),
                'ShiZhi': base.get('ShiZhi', 0),
                'ShiYingLv': base.get('ShiYingLv', 0) / 1000.0,
                'ShiJingLv': base.get('ShiJingLv', 0) / 1000.0,
                'ZhenFu': base.get('ZhenFu', 0) / 1000.0,
                'LianZhangTian': base.get('LianZhangTian', 0)
            }

            return df

        except Exception as e:
            return None