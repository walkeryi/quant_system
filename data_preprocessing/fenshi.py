import requests
import pandas as pd
import logging
from config import HSA_TOKEN

logger = logging.getLogger(__name__)


class FenshiDataProvider:
    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_fenshi"

    def __init__(self, token: str = HSA_TOKEN):
        self.token = token

    def fetch(self, code: str, fetch_all: bool = True) -> pd.DataFrame | None:
        params = {'token': self.token, 'code': code, 'all': 1 if fetch_all else 0}
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
            # --- 修复后的健壮字段解析 ---
            # 判断列是否存在：如果存在则转换类型，如果不存在则直接赋予默认值
            df['price'] = df['JiaGe'].astype(float) / 1000.0 if 'JiaGe' in df else 0.0
            # 如果没有均价 (JunJia)，则默认使用当前价 (price)
            df['avg_price'] = df['JunJia'].astype(float) / 1000.0 if 'JunJia' in df else df['price']
            df['pct_chg'] = df['ZhangFu'].astype(float) / 1000.0 if 'ZhangFu' in df else 0.0
            df['time'] = df['ShiJian'] if 'ShiJian' in df else ""

            df['minute_volume'] = df['ZongLiang'].astype(float) if 'ZongLiang' in df else 0.0

            # --- 提取额外字段（用于弹窗）---
            df['nei_pan'] = df['NeiPan'].astype(float) if 'NeiPan' in df else 0.0
            df['wai_pan'] = df['WaiPan'].astype(float) if 'WaiPan' in df else 0.0
            df['huan_shou'] = df['HuanShou'].astype(float) / 1000.0 if 'HuanShou' in df else 0.0
            df['liang_bi'] = df['LiangBi'].astype(float) / 1000.0 if 'LiangBi' in df else 0.0
            df['wei_bi'] = df['WeiBi'].astype(float) / 1000.0 if 'WeiBi' in df else 0.0

            result_df = df[['time', 'price', 'avg_price', 'minute_volume', 'pct_chg',
                            'nei_pan', 'wai_pan', 'huan_shou', 'liang_bi', 'wei_bi']].copy()

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