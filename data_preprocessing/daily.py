# data_preprocessing/daily.py
import requests
import pandas as pd
from common.storage import Storage
from common.utils import setup_logger, log_exceptions
from config import HSA_TOKEN, DAILY_DATA_DIR  # 稍后在 config.py 添加
import os

logger = setup_logger(__name__)


class DailyDataProvider:
    """获取沪深个股日线数据（散户量化API）"""

    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_rixian"

    # 如果需要 HTTPS，可添加 https_url

    def __init__(self, token: str = HSA_TOKEN):
        self.token = token
        # 确保日线数据存储目录存在
        os.makedirs(DAILY_DATA_DIR, exist_ok=True)

    def _get_cache_path(self, code: str, all_data: bool) -> str:
        """生成缓存文件路径，all=1 时缓存全部数据，否则单独缓存最近100条"""
        suffix = "all" if all_data else "latest"
        return os.path.join(DAILY_DATA_DIR, f"{code}_{suffix}.csv")

    @log_exceptions(logger)
    def fetch(self, code: str, all_data: bool = False, use_cache: bool = True) -> pd.DataFrame | None:
        """
        获取个股日线数据
        :param code: 股票代码，如 '000001'
        :param all_data: True=获取2000年以来所有数据，False=仅最新100条
        :param use_cache: 是否使用本地缓存（仅当 all_data=False 时缓存才有意义，因为全部数据不常变）
        :return: 清洗后的 DataFrame，列名统一为英文，索引为日期，失败返回 None
        """
        cache_file = self._get_cache_path(code, all_data)

        # 尝试从缓存加载（仅当请求的是全部数据时，缓存有效时间可设长一些）
        if use_cache and all_data and Storage.is_cache_fresh(cache_file, max_age_days=7):  # 一周更新一次
            cached = Storage.load_csv(cache_file, parse_dates=True)
            if cached is not None:
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

            # 提取行情列表
            records = data.get('data', [])
            if not records:
                logger.warning(f"No daily data for {code}")
                return pd.DataFrame()

            # 转换为 DataFrame
            df = pd.DataFrame(records)

            # 列名映射（中文 -> 英文）
            column_map = {
                'RiQi': 'date',
                'KaiPan': 'open',
                'ZuiGao': 'high',
                'ZuiDi': 'low',
                'ShouPan': 'close',
                'ZongLiang': 'volume',  # 单位：手
                'JinE': 'amount'  # 单位：元
            }
            df.rename(columns=column_map, inplace=True)

            # 日期处理
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)

            # 价格单位转换：从 0.1分 转换为 元
            price_cols = ['open', 'high', 'low', 'close']
            df[price_cols] = df[price_cols] / 1000.0  # 因为 1元 = 1000 * 0.1分

            # 确保数据类型正确
            df[price_cols] = df[price_cols].astype(float)
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce').astype(float)
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').astype(float)

            # 保存到缓存（如果是全部数据）
            if all_data:
                Storage.save_csv(df, cache_file)

            logger.info(f"Fetched {len(df)} daily records for {code}")
            return df

        except requests.RequestException as e:
            logger.error(f"Request failed for {code}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error for {code}: {e}")
            return None

    def fetch_range(self, code: str, start_date: str, end_date: str) -> pd.DataFrame | None:
        """
        获取指定日期范围的日线数据（通过获取全部数据后筛选，适合数据量不大的情况）
        注意：此方法会先尝试获取全部数据，再按日期切片。
        如果已有缓存，则直接从缓存筛选。
        """
        df = self.fetch(code, all_data=True, use_cache=True)
        if df is None or df.empty:
            return None
        mask = (df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))
        return df.loc[mask]