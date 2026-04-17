# -*- coding: utf-8 -*-
"""
交易日历数据获取 - 优化版
- 支持并发请求 (ThreadPoolExecutor)
- 优化 Pandas 迭代性能 (向量化操作)
- 支持批量查询
- 预留多市场接口
"""
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Optional
from quant_system.common.storage import Storage
from quant_system.common.utils import log_exceptions, setup_logger
from quant_system.config import HSA_TOKEN, TRADE_CALENDAR_CACHE
import os

logger = setup_logger(__name__)


class TradeCalendarProvider:
    """查询交易日历，支持本地缓存全年数据"""
    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_rili"

    # 支持的市场
    MARKETS = {
        'A': 'A股 (沪深)',
        'HK': '港股',
        'US': '美股',
    }

    def __init__(self, token: str = HSA_TOKEN, market: str = 'A'):
        self.token = token
        self.market = market
        self._cache: dict[str, bool] | None = None
        self._holiday_names: dict[str, str] = {}

    @property
    def cache_path(self) -> str:
        """根据市场返回不同的缓存路径"""
        if self.market == 'A':
            return TRADE_CALENDAR_CACHE
        return TRADE_CALENDAR_CACHE.replace('.csv', f'_{self.market.lower()}.csv')

    @log_exceptions(logger)
    def is_trading_day(self, date_str: str = None) -> bool | None:
        """
        查询指定日期是否为交易日
        :param date_str: 格式 'YYYY-MM-DD'，默认今天
        :param market: 市场标识，默认 'A' (A股)
        :return: True=交易日, False=非交易日, None=查询失败
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')

        # 1. 优先从内存缓存读取
        if self._cache is not None and date_str in self._cache:
            return self._cache[date_str]

        # 2. 从本地缓存加载
        if self._load_cache_for_year(date_str[:4]):
            if date_str in self._cache:
                return self._cache[date_str]

        # 3. 请求API
        return self._fetch_from_api(date_str)

    def _fetch_from_api(self, date_str: str) -> bool | None:
        """从API获取单日数据"""
        params = {'token': self.token, 'date': date_str}
        try:
            logger.info(f"Querying API for {date_str}")
            resp = requests.get(self.API_URL, params=params, timeout=10)
            data = resp.json()
            if data.get('ret') != 200:
                logger.error(f"API error: {data.get('msg')}")
                return None
            is_trade = data.get('trade') == 1
            if self._cache is None:
                self._cache = {}
            self._cache[date_str] = is_trade
            return is_trade
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    def _load_cache_for_year(self, year: str) -> bool:
        """加载指定年份的缓存数据到内存 - 使用向量化操作优化"""
        cache_path = self.cache_path
        if not os.path.exists(cache_path):
            return False
        try:
            df = pd.read_csv(cache_path)
            if 'date' not in df.columns or 'trade' not in df.columns:
                return False
            df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
            year_mask = df['date'].dt.year == int(year)
            year_df = df[year_mask]
            if year_df.empty:
                return False
            # 优化：使用 dict + zip 替代 iterrows，速度提升 10-100 倍
            self._cache = dict(zip(
                year_df['date'].dt.strftime('%Y-%m-%d'),
                year_df['trade'].astype(bool)
            ))
            logger.info(f"Loaded {len(self._cache)} trading days for {year} from cache")
            return True
        except Exception as e:
            logger.error(f"Failed to load trade calendar cache: {e}")
            return False

    def prefetch_year(self, year: int, max_workers: int = 10,
                      progress_callback=None) -> bool:
        """
        预获取某年的全部交易日并缓存 - 并发优化版

        :param year: 年份
        :param max_workers: 最大并发线程数，默认10
        :param progress_callback: 进度回调函数，签名为 (current, total, date_str) -> None
        :return: 是否成功
        """
        from datetime import timedelta
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        all_dates = pd.date_range(start, end, freq='D')
        date_strs = [d.strftime('%Y-%m-%d') for d in all_dates]
        total = len(date_strs)

        results = []
        completed = 0
        failed = 0

        # 使用线程池并发请求
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_date = {
                executor.submit(self.is_trading_day, date_str): date_str
                for date_str in date_strs
            }

            for future in as_completed(future_to_date):
                date_str = future_to_date[future]
                completed += 1
                try:
                    is_trade = future.result()
                    if is_trade is not None:
                        results.append({'date': date_str, 'trade': int(is_trade)})
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    logger.warning(f"Failed to get {date_str}: {e}")

                # 报告进度
                if progress_callback:
                    progress_callback(completed, total, date_str)

        if results:
            df = pd.DataFrame(results)
            Storage.save_csv(df, self.cache_path)
            logger.info(f"Prefetched {len(results)} days for {year}, {failed} failed")

        return len(results) > 0

    def batch_is_trading_days(self, date_strs: list[str],
                              max_workers: int = 20) -> dict[str, bool | None]:
        """
        批量查询多个日期是否为交易日 - 并发优化

        :param date_strs: 日期字符串列表 ['YYYY-MM-DD', ...]
        :param max_workers: 最大并发数
        :return: {date_str: is_trading_day}
        """
        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_date = {
                executor.submit(self.is_trading_day, date_str): date_str
                for date_str in date_strs
            }

            for future in as_completed(future_to_date):
                date_str = future_to_date[future]
                try:
                    results[date_str] = future.result()
                except Exception:
                    results[date_str] = None

        return results

    def get_trading_days_between(self, start_date: str, end_date: str) -> list[str]:
        """
        获取两个日期间的交易日列表

        :param start_date: 开始日期 'YYYY-MM-DD'
        :param end_date: 结束日期 'YYYY-MM-DD'
        :return: 交易日列表
        """
        all_dates = pd.date_range(start_date, end_date, freq='D')
        date_strs = [d.strftime('%Y-%m-%d') for d in all_dates]

        # 先尝试从缓存/数据库获取
        self._ensure_year_range_loaded(date_strs)

        trading_days = []
        for date_str in date_strs:
            is_trade = self.is_trading_day(date_str)
            if is_trade is True:
                trading_days.append(date_str)

        return trading_days

    def get_next_trading_day(self, date_str: str, n: int = 1) -> str | None:
        """
        获取指定日期的T+N交易日

        :param date_str: 起始日期 'YYYY-MM-DD'
        :param n: 偏移天数，正数为未来，负数为过去
        :return: T+N 的交易日日期字符串，None表示未找到
        """
        current = datetime.strptime(date_str, '%Y-%m-%d')
        direction = 1 if n >= 0 else -1
        steps = abs(n)

        for _ in range(steps + 365):  # 最多查找一年
            current += timedelta(days=direction)
            date_str = current.strftime('%Y-%m-%d')
            if self.is_trading_day(date_str) is True:
                return date_str

        return None

    def count_trading_days(self, start_date: str, end_date: str) -> int:
        """
        计算两个日期间的交易日数量

        :param start_date: 开始日期 'YYYY-MM-DD'
        :param end_date: 结束日期 'YYYY-MM-DD'
        :return: 交易日天数
        """
        return len(self.get_trading_days_between(start_date, end_date))

    def _ensure_year_range_loaded(self, date_strs: list[str]):
        """确保日期范围内的年份数据都已加载"""
        years = set(d[:4] for d in date_strs)
        for year in years:
            if not self._load_cache_for_year(year):
                # 如果缓存不存在，尝试预加载该年
                self.prefetch_year(int(year))

    def clear_cache(self):
        """清空内存缓存"""
        self._cache = None
        self._holiday_names = {}

    def get_holiday_name(self, date_str: str) -> str | None:
        """
        获取指定日期的节假日名称（如果已知）

        :param date_str: 日期 'YYYY-MM-DD'
        :return: 节假日名称，如 '国庆节'、'春节'，None 表示非节假日或未知
        """
        return self._holiday_names.get(date_str)

    def set_holiday_name(self, date_str: str, name: str):
        """设置节假日名称"""
        self._holiday_names[date_str] = name


# 预定义的A股节假日（用于快速判断，不需要网络请求）
CHINA_HOLIDAYS = {
    # 元旦
    '0101': '元旦',
    # 春节 (每年不同，需动态计算)
    # 清明节 (每年不同)
    # 劳动节
    '0501': '劳动节',
    '0502': '劳动节',
    '0503': '劳动节',
    # 国庆节
    '1001': '国庆节',
    '1002': '国庆节',
    '1003': '国庆节',
    '1004': '国庆节',
    '1005': '国庆节',
    '1006': '国庆节',
    '1007': '国庆节',
}

CHINA_HOLIDAYS_RANGES = {
    # 春节假期范围 (农历除夕到初七，通常)
    'spring_festival': {'start_offset': -2, 'end_offset': 7},
    # 清明节
    'qingming': {'start_offset': -1, 'end_offset': 1},
    # 劳动节
    'labour_day': {'start_offset': 0, 'end_offset': 2},
    # 国庆节
    'national_day': {'start_offset': 0, 'end_offset': 6},
}
