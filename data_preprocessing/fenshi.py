import requests
import pandas as pd
import logging
from config import HSA_TOKEN

logger = logging.getLogger(__name__)


class FenshiDataProvider:
    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_fenshi"

    def __init__(self, token: str = HSA_TOKEN):
        self.token = token

    def fetch(self, code: str) -> pd.DataFrame | None:
        params = {'token': self.token, 'code': code, 'all': 1}
        try:
            resp = requests.get(self.API_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get('ret') != 200:
                logger.error(f"API Error for {code}: {data.get('msg')}")
                return None

            base = data.get('base', {})
            points = data.get('data', [])
            if not points: return None

            df = pd.DataFrame(points)
            # 单位转换: 价格和均价 (0.1分 -> 元), 涨幅 (0.001% -> %)
            df['price'] = df['JiaGe'] / 1000.0
            df['avg_price'] = df['JunJia'] / 1000.0
            df['pct_chg'] = df['ZhangFu'] / 1000.0
            df['time'] = df['ShiJian']

            df['minute_volume'] = df['ZongLiang'].astype(float)

            result_df = df[['time', 'price', 'avg_price', 'minute_volume', 'pct_chg']].copy()

            # 附加完整 base 信息用于 UI 面板 (10个字段)
            result_df.attrs['base'] = {
                'name': base.get('name'),
                'code': base.get('code'),
                'date': base.get('date'),
                'KaiPan': base.get('KaiPan', 0) / 1000.0,
                'ZuiGao': base.get('ZuiGao', 0) / 1000.0,
                'ZuiDi': base.get('ZuiDi', 0) / 1000.0,
                'ZuoShou': base.get('ZuoShou', 0) / 1000.0,
                'ZhenFu': base.get('ZhenFu', 0) / 1000.0,
                'NeiWaiBi': base.get('NeiWaiBi', 0) / 1000.0,
                'ShiYingLv': base.get('ShiYingLv', 0) / 1000.0,
                'ShiJingLv': base.get('ShiJingLv', 0) / 1000.0,
                'ShiZhi': base.get('ShiZhi', 0)
            }
            return result_df
        except Exception as e:
            logger.error(f"Fenshi Preprocessing Error: {str(e)}")
            return None