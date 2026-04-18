# -*- coding: utf-8 -*-
"""
数据层
提供所有数据的获取、缓存、持久化功能
"""
from .providers import (
    StockListProvider,
    DailyDataProvider,
    FenshiDataProvider,
    WeeklyDataProvider,
    MonthlyDataProvider,
    TradeCalendarProvider,
)
from .storage import (
    Storage,
    DBManager,
    StateManager,
    init_db,
    upsert_stock_quote,
    bulk_upsert_from_df,
    load_stock_list_df,
    get_latest_update_date,
)

__all__ = [
    'StockListProvider',
    'DailyDataProvider',
    'FenshiDataProvider',
    'WeeklyDataProvider',
    'MonthlyDataProvider',
    'TradeCalendarProvider',
    'Storage',
    'DBManager',
    'StateManager',
    'init_db',
    'upsert_stock_quote',
    'bulk_upsert_from_df',
    'load_stock_list_df',
    'get_latest_update_date',
    'DataPreprocessor',
]
