# data_preprocessing/fetcher.py
import logging
from .stock_list import StockListProvider
from .trade_calendar import TradeCalendar
from .daily import DailyDataProvider
from .fenshi import FenshiDataProvider   # 新增导入
import pandas as pd

logger = logging.getLogger('quant_system')

class DataPreprocessor:
    def __init__(self):
        self.stock_list_provider = StockListProvider()
        self.trade_calendar = TradeCalendar()
        self.daily_provider = DailyDataProvider()
        self.fenshi_provider = FenshiDataProvider()   # 新增

    def get_stock_list(self, use_cache: bool = True):
        try:
            return self.stock_list_provider.fetch(use_cache=use_cache)
        except Exception as e:
            logger.exception("get_stock_list 异常")
            return None

    def is_trading_day(self, date_str: str = None):
        try:
            return self.trade_calendar.is_trading_day(date_str)
        except Exception as e:
            logger.exception("is_trading_day 异常")
            return None

    def get_daily_data(self, code: str, start_date: str = None, end_date: str = None, all_data: bool = False):
        try:
            if start_date and end_date:
                return self.daily_provider.fetch_range(code, start_date, end_date)
            else:
                return self.daily_provider.fetch(code, all_data=all_data, use_cache=True)
        except Exception as e:
            logger.exception(f"get_daily_data 异常 (code={code})")
            return None

    def get_fenshi_data(self, code: str):
        """获取分时数据"""
        try:
            return self.fenshi_provider.fetch(code)
        except Exception as e:
            logger.exception(f"get_fenshi_data 异常 (code={code})")
            raise  # 重新抛出异常，让上层处理

    def save_fenshi_to_db(self, df: pd.DataFrame) -> int:
        """保存分时数据到数据库"""
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
            logger.error("DataFrame 缺少 code 或 date 信息")
            return 0

        records = []
        for _, row in df.iterrows():
            time_str = str(row['time']).strip()
            if len(time_str) == 5:
                time_str += ":00"

            price_val = float(row['price'])
            volume_val = int(row['volume'])
            # 计算成交额（元）
            amount_val = price_val * volume_val * 100

            records.append((
                code,
                trade_date,
                time_str,
                price_val,
                volume_val,
                amount_val
            ))