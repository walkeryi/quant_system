# quant_system/data_preprocessing/fetcher.py
import logging
from .stock_list import StockListProvider
from .trade_calendar import TradeCalendar
from .daily import DailyDataProvider
from .fenshi import FenshiDataProvider
from .weekly import WeeklyDataProvider
from .monthly import MonthlyDataProvider
import pandas as pd
from common.storage import Storage

logger = logging.getLogger('quant_system')


class DataPreprocessor:
    def __init__(self):
        self.storage = Storage()
        self.stock_list_provider = StockListProvider()
        self.trade_calendar = TradeCalendar()
        self.daily_provider = DailyDataProvider()
        self.fenshi_provider = FenshiDataProvider()
        self.weekly_provider = WeeklyDataProvider()
        self.monthly_provider = MonthlyDataProvider()

    def get_daily_data(self, code: str, start_date: str = None, end_date: str = None, all_data: bool = False):
        """整合后的日线获取逻辑"""
        status = self.storage.get_stock_status(code)
        if status == 302:
            logger.warning(f"代码 {code} 已标记为无效/退市，跳过请求")
            return "DELISTED"

        try:
            cache_path = f"quant_system/cache/daily/{code}.parquet"
            df = None

            # 日线如果获取全量数据，同样校验是否在 1 天内
            if self.storage.is_cache_fresh(cache_path, max_age_days=1):
                df = self.storage.load_parquet(cache_path)

            if df is None:
                if start_date and end_date:
                    result = self.daily_provider.fetch_range(code, start_date, end_date)
                else:
                    result = self.daily_provider.fetch(code, all_data=all_data, use_cache=True)

                ret_code = getattr(result, 'ret', 200)
                if hasattr(result, 'attrs'):
                    ret_code = result.attrs.get('ret', ret_code)

                if ret_code == 302 or (isinstance(result, str) and "302" in result):
                    self.storage.update_stock_status(code, 302)
                    return "DELISTED"

                df = result
                if df is not None and not (isinstance(df, pd.DataFrame) and df.empty):
                    self.storage.save_parquet(df, cache_path)

            return df
        except Exception as e:
            if "302" in str(e):
                self.storage.update_stock_status(code, 302)
                return "DELISTED"
            logger.exception(f"get_daily_data 异常: {code}")
            return None

    def _get_kline_data_logic(self, code: str, provider, cache_type: str):
        """通用K线获取逻辑：严格的 1天过期校验 -> API (请求最新100笔) -> 保存二进制缓存"""
        status = self.storage.get_stock_status(code)
        if status == 302:
            return "DELISTED"

        try:
            cache_path = f"quant_system/cache/{cache_type}/{code}.parquet"
            df = None

            # 核心修复：检查缓存是否有效，避免“最新100笔”永远停留在历史某一天
            if self.storage.is_cache_fresh(cache_path, max_age_days=1):
                df = self.storage.load_parquet(cache_path)

            if df is None or df.empty:
                logger.info(f"缓存失效或过期，向 {cache_type} API 请求最新100笔数据: {code}")
                df = provider.fetch(code)

                if df is not None and not df.empty:
                    ret_code = getattr(df, 'ret', 200)
                    if hasattr(df, 'attrs'):
                        ret_code = df.attrs.get('ret', ret_code)

                    if ret_code == 302:
                        self.storage.update_stock_status(code, 302)
                        return "DELISTED"

                    self.storage.save_parquet(df, cache_path)

            return df
        except Exception as e:
            logger.exception(f"获取 {cache_type} 数据异常: {code}")
            return None

    def get_weekly_data(self, code: str):
        """获取周线数据（100笔，带智能缓存）"""
        return self._get_kline_data_logic(code, self.weekly_provider, "weekly")

    def get_monthly_data(self, code: str):
        """获取月线数据（100笔，带智能缓存）"""
        return self._get_kline_data_logic(code, self.monthly_provider, "monthly")

    # ========= 下方的原有接口原样保留 =========
    def get_stock_list(self, use_cache: bool = True):
        try:
            return self.stock_list_provider.fetch(use_cache=use_cache)
        except Exception as e:
            logger.exception("get_stock_list 异常")
            return None, None

    def is_trading_day(self, date_str: str = None):
        try:
            return self.trade_calendar.is_trading_day(date_str)
        except Exception as e:
            logger.exception("is_trading_day 异常")
            return None

    def get_fenshi_data(self, code: str):
        try:
            result = self.fenshi_provider.fetch(code)
            ret_code = getattr(result, 'ret', 200)
            if hasattr(result, 'attrs'):
                ret_code = result.attrs.get('ret', ret_code)

            if ret_code == 302 or (isinstance(result, str) and "302" in result):
                return "DELISTED"
            return result
        except Exception as e:
            if "302" in str(e):
                return "DELISTED"
            logger.exception(f"get_fenshi_data 异常 (code={code})")
            raise

    def save_fenshi_to_db(self, df: pd.DataFrame) -> int:
        try:
            return self.fenshi_provider.save_to_db(df)
        except Exception as e:
            logger.exception("save_fenshi_to_db 异常")
            return 0

    def save_to_db(self, df: pd.DataFrame) -> int:
        base = df.attrs.get('base', {})
        code = base.get('code')
        trade_date = base.get('date')
        if not code or not trade_date:
            return 0

        records = []
        for _, row in df.iterrows():
            time_str = str(row['time']).strip()
            if len(time_str) == 5:
                time_str += ":00"

            price_val = float(row['price'])
            volume_val = int(row['volume'])
            amount_val = price_val * volume_val * 100

            records.append((code, trade_date, time_str, price_val, volume_val, amount_val))
        return len(records)