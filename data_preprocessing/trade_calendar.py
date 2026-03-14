import requests
import pandas as pd
from datetime import datetime
from common.storage import Storage
from common.utils import setup_logger, log_exceptions, validate_date
from config import HSA_TOKEN, CACHE_DIR
import os

logger = setup_logger(__name__)

class TradeCalendar:
    """查询交易日历，支持本地缓存全年数据"""

    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_rili"
    CACHE_FILE = os.path.join(CACHE_DIR, "trade_calendar.csv")

    def __init__(self, token: str = HSA_TOKEN):
        self.token = token
        self._cache = None  # 内存缓存，加速同一次会话的重复查询

    @log_exceptions(logger)
    def is_trading_day(self, date_str: str = None) -> bool | None:
        """
        查询指定日期是否为交易日
        :param date_str: 格式 'YYYY-MM-DD'，默认今天
        :return: True=交易日, False=非交易日, None=查询失败
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')

        # 先尝试从内存缓存获取
        if self._cache is not None and date_str in self._cache:
            return self._cache[date_str]

        # 尝试从文件缓存加载全年数据
        if self._load_cache_for_year(date_str[:4]):  # 根据年份加载
            if date_str in self._cache:
                return self._cache[date_str]

        # 否则调用API
        params = {'token': self.token, 'date': date_str}
        try:
            logger.info(f"Querying API for {date_str}")
            resp = requests.get(self.API_URL, params=params, timeout=10)
            data = resp.json()
            if data.get('ret') != 200:
                logger.error(f"API error: {data.get('msg')}")
                return None
            is_trade = data.get('trade') == 1
            # 更新内存缓存
            if self._cache is None:
                self._cache = {}
            self._cache[date_str] = is_trade
            return is_trade
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    def _load_cache_for_year(self, year: str) -> bool:
        """加载指定年份的缓存数据到内存，成功返回True"""
        if not os.path.exists(self.CACHE_FILE):
            return False
        try:
            df = pd.read_csv(self.CACHE_FILE)
            if 'date' not in df.columns or 'trade' not in df.columns:
                return False
            # 筛选年份
            df['date'] = pd.to_datetime(df['date'])
            year_mask = df['date'].dt.year == int(year)
            year_df = df[year_mask]
            if year_df.empty:
                return False
            self._cache = {row['date'].strftime('%Y-%m-%d'): bool(row['trade']) for _, row in year_df.iterrows()}
            logger.info(f"Loaded {len(self._cache)} trading days for {year} from cache")
            return True
        except Exception as e:
            logger.error(f"Failed to load trade calendar cache: {e}")
            return False

    def prefetch_year(self, year: int):
        """预获取某年的全部交易日并缓存（可选，可后台调用）"""
        from datetime import timedelta
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        all_dates = pd.date_range(start, end, freq='D')
        results = []
        for date in all_dates:
            date_str = date.strftime('%Y-%m-%d')
            is_trade = self.is_trading_day(date_str)  # 会走API并更新缓存
            if is_trade is not None:
                results.append({'date': date_str, 'trade': int(is_trade)})
            else:
                logger.warning(f"Failed to get {date_str}, skipping")
        # 保存到文件
        df = pd.DataFrame(results)
        Storage.save_csv(df, self.CACHE_FILE)
        logger.info(f"Prefetched {len(results)} days for {year}")