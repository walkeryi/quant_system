# data_preprocessing/fetcher.py
import logging
from .stock_list import StockListProvider
from .trade_calendar import TradeCalendar
from .daily import DailyDataProvider

# 获取统一日志器
logger = logging.getLogger('quant_system')

class DataPreprocessor:
    "数据预处理类"
    def __init__(self):
        self.stock_list_provider = StockListProvider()
        self.trade_calendar = TradeCalendar()
        self.daily_provider = DailyDataProvider()

    def get_stock_list(self, use_cache: bool = True):
        """获取股票列表，发生异常时记录日志并返回 None"""
        try:
            return self.stock_list_provider.fetch(use_cache=use_cache)
        except Exception as e:
            logger.exception("get_stock_list 异常")
            return None

    def is_trading_day(self, date_str: str = None):
        """查询交易日，发生异常时记录日志并返回 None"""
        try:
            return self.trade_calendar.is_trading_day(date_str)
        except Exception as e:
            logger.exception("is_trading_day 异常")
            return None

    def get_daily_data(self, code: str, start_date: str = None, end_date: str = None, all_data: bool = False):
        """
        获取个股日线数据
        :param code: 股票代码
        :param start_date: 开始日期 YYYY-MM-DD，如果提供则返回该区间数据（会尝试获取全部数据后切片）
        :param end_date: 结束日期 YYYY-MM-DD
        :param all_data: 是否获取全部历史数据（优先级低于 start_date/end_date）
        :return: DataFrame 或 None
        """
        try:
            if start_date and end_date:
                return self.daily_provider.fetch_range(code, start_date, end_date)
            else:
                return self.daily_provider.fetch(code, all_data=all_data, use_cache=True)
        except Exception as e:
            logger.exception(f"get_daily_data 异常 (code={code})")
            return None