# -*- coding: utf-8 -*-
"""
数据获取层 - providers
所有数据获取逻辑的聚合模块
"""
from .stock_list import StockListProvider
from .daily import DailyDataProvider
from .fenshi import FenshiDataProvider
from .weekly import WeeklyDataProvider
from .monthly import MonthlyDataProvider
from .calendar import TradeCalendarProvider

__all__ = [
    'StockListProvider',
    'DailyDataProvider',
    'FenshiDataProvider',
    'WeeklyDataProvider',
    'MonthlyDataProvider',
    'TradeCalendarProvider',
]
