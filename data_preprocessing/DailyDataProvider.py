# data_preprocessing/daily.py (在文件开头或末尾添加以下类)
import requests
import pandas as pd
import logging
from common.storage import Storage
from config import HSA_TOKEN, DAILY_DATA_DIR
import os

logger = logging.getLogger('quant_system')


class DailyDataProvider:
    """获取个股日线数据，支持缓存"""

    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_daily"  # 假设的日线接口，请替换为实际地址

    def __init__(self, token: str = HSA_TOKEN):
        self.token = token
        self.cache_dir = DAILY_DATA_DIR

    def _get_cache_path(self, code):
        """生成缓存文件路径"""
        return os.path.join(self.cache_dir, f"{code}.csv")

    def fetch(self, code: str, all_data: bool = False, use_cache: bool = True) -> pd.DataFrame | None:
        """
        获取股票日线数据
        :param code: 股票代码
        :param all_data: 是否获取全部历史数据
        :param use_cache: 是否使用缓存
        :return: DataFrame 或 None
        """
        cache_path = self._get_cache_path(code)
        if use_cache and os.path.exists(cache_path):
            # 检查缓存是否新鲜（例如1天内）
            if Storage.is_cache_fresh(cache_path, max_age_days=1):
                df = Storage.load_csv(cache_path, index_col=0, parse_dates=['date'])
                if df is not None:
                    logger.info(f"Loaded daily data for {code} from cache")
                    return df

        # 从 API 获取
        params = {'token': self.token, 'code': code}
        if not all_data:
            # 如果不获取全部数据，可能需要指定日期范围，这里简化处理
            pass
        try:
            logger.info(f"Fetching daily data for {code} from API...")
            resp = requests.get(self.API_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get('ret') != 200:
                logger.error(f"API error: {data.get('msg')}")
                return None
            records = data.get('data', [])
            if not records:
                logger.warning(f"No daily data for {code}")
                return None
            df = pd.DataFrame(records)
            # 将日期列设为索引并排序
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
            # 保存缓存
            Storage.save_csv(df, cache_path)
            return df
        except Exception as e:
            logger.exception(f"Failed to fetch daily data for {code}: {e}")
            return None

    def fetch_range(self, code: str, start_date: str, end_date: str) -> pd.DataFrame | None:
        """
        获取指定日期区间的日线数据
        """
        df = self.fetch(code, all_data=True)  # 先获取全部数据
        if df is None or df.empty:
            return None
        # 切片
        mask = (df.index >= start_date) & (df.index <= end_date)
        return df.loc[mask].copy()