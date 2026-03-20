# data_preprocessing/daily.py
import requests
import pandas as pd
from common.storage import Storage
from common.utils import setup_logger, log_exceptions
from config import HSA_TOKEN, DAILY_DATA_DIR
import os

logger = setup_logger(__name__)

class DailyDataProvider:
    """获取沪深个股日线数据（散户量化API）"""

    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_rixian"

    def __init__(self, token: str = HSA_TOKEN):
        self.token = token
        os.makedirs(DAILY_DATA_DIR, exist_ok=True)

    def _get_cache_path(self, code: str, all_data: bool) -> str:
        suffix = "all" if all_data else "latest"
        return os.path.join(DAILY_DATA_DIR, f"{code}_{suffix}.csv")

    @log_exceptions(logger)
    def fetch(self, code: str, all_data: bool = False, use_cache: bool = True) -> pd.DataFrame | None:
        cache_file = self._get_cache_path(code, all_data)

        # 尝试从缓存加载
        if use_cache and all_data and Storage.is_cache_fresh(cache_file, max_age_days=1):
            cached = Storage.load_csv(cache_file)
            if cached is not None and not cached.empty:
                if 'date' in cached.columns:
                    cached['date'] = pd.to_datetime(cached['date'])
                    cached.set_index('date', inplace=True)
                    cached.sort_index(inplace=True)
                    logger.info(f"Loaded daily data for {code} (all) from cache")
                    return cached

        # 请求 API
        params = {
            'token': self.token,
            'code': code,
            'all': 1 if all_data else 0
        }
        try:
            logger.info(f"Fetching daily data for {code} from API...")
            resp = requests.get(self.API_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get('ret') != 200:
                logger.error(f"API error for {code}: {data.get('msg')}")
                return None

            base = data.get('base', {})
            records = data.get('data', [])
            if not records:
                logger.warning(f"No daily data for {code}")
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

            # 其他数值转换
            if 'volume' in df.columns:
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            if 'amount' in df.columns:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)

            # 将 base 数据挂载到 attrs 供 UI 使用
            df.attrs['base'] = {
                'name': base.get('name', ''),
                'code': base.get('code', code),
                'ShiZhi': base.get('ShiZhi', 0),
                'ShiYingLv': base.get('ShiYingLv', 0) / 1000.0,
                'ShiJingLv': base.get('ShiJingLv', 0) / 1000.0,
                'ZhenFu': base.get('ZhenFu', 0) / 1000.0,
                'LianZhangTian': base.get('LianZhangTian', 0)
            }

            # 保存到缓存（如果是全部数据）
            if all_data:
                df_to_save = df.reset_index()
                Storage.save_csv(df_to_save, cache_file)

            logger.info(f"Fetched {len(df)} daily records for {code}")
            return df

        except Exception as e:
            logger.exception(f"Unexpected error for {code}: {e}")
            return None

    def fetch_range(self, code: str, start_date: str, end_date: str) -> pd.DataFrame | None:
        df = self.fetch(code, all_data=True, use_cache=True)
        if df is None or df.empty:
            return None
        mask = (df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))
        return df.loc[mask]