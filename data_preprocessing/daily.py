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

        # 尝试从缓存加载（仅当请求的是全部数据时）
        if use_cache and all_data and Storage.is_cache_fresh(cache_file, max_age_days=7):
            cached = Storage.load_csv(cache_file)
            if cached is not None and not cached.empty:
                # 确保日期列存在并设为索引
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

            records = data.get('data', [])
            if not records:
                logger.warning(f"No daily data for {code}")
                return pd.DataFrame()

            df = pd.DataFrame(records)

            column_map = {
                'RiQi': 'date',
                'KaiPan': 'open',
                'ZuiGao': 'high',
                'ZuiDi': 'low',
                'ShouPan': 'close',
                'ZongLiang': 'volume',
                'JinE': 'amount'
            }
            df.rename(columns=column_map, inplace=True)

            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)

            price_cols = ['open', 'high', 'low', 'close']
            df[price_cols] = df[price_cols] / 1000.0

            df[price_cols] = df[price_cols].astype(float)
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce').astype(float)
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').astype(float)

            # 保存到缓存（如果是全部数据）
            if all_data:
                # 保存时重置索引，将日期作为普通列，便于以后读取
                df_to_save = df.reset_index()
                Storage.save_csv(df_to_save, cache_file)

            logger.info(f"Fetched {len(df)} daily records for {code}")
            return df

        except requests.RequestException as e:
            logger.error(f"Request failed for {code}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error for {code}: {e}")
            return None

    def fetch_range(self, code: str, start_date: str, end_date: str) -> pd.DataFrame | None:
        df = self.fetch(code, all_data=True, use_cache=True)
        if df is None or df.empty:
            return None
        mask = (df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))
        return df.loc[mask]