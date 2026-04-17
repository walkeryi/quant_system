# -*- coding: utf-8 -*-
"""
日历服务 - 优化版
提供交易日历查询、T+N计算、多市场支持
"""
from datetime import datetime, timedelta
from typing import Literal
from quant_system.data.providers import TradeCalendarProvider


class CalendarService:
    """交易日历查询服务 - 扩展版"""

    def __init__(self, market: str = 'A'):
        self.market = market
        self.provider = TradeCalendarProvider(market=market)

    def is_trading_day(self, date_str: str = None) -> bool | None:
        """查询指定日期是否为交易日"""
        return self.provider.is_trading_day(date_str)

    def prefetch_year(self, year: int, max_workers: int = 10,
                      progress_callback=None) -> bool:
        """
        预加载指定年份的日历数据

        :param year: 年份
        :param max_workers: 最大并发数
        :param progress_callback: 进度回调 (current, total, date_str) -> None
        """
        return self.provider.prefetch_year(year, max_workers, progress_callback)

    def get_next_trading_day(self, date_str: str = None, n: int = 1) -> str | None:
        """
        获取 T+N 交易日

        :param date_str: 起始日期，默认今天
        :param n: 偏移天数，正数为未来，负数为过去
        :return: T+N 的交易日日期字符串

        示例:
            service.get_next_trading_day('2024-01-01', 5)  # 获取1月1日的第5个交易日
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        return self.provider.get_next_trading_day(date_str, n)

    def get_trading_days_between(self, start_date: str, end_date: str) -> list[str]:
        """
        获取两个日期间的交易日列表

        :param start_date: 开始日期 'YYYY-MM-DD'
        :param end_date: 结束日期 'YYYY-MM-DD'
        :return: 交易日列表

        示例:
            service.get_trading_days_between('2024-01-01', '2024-01-31')
        """
        return self.provider.get_trading_days_between(start_date, end_date)

    def count_trading_days(self, start_date: str, end_date: str) -> int:
        """
        计算两个日期间的交易日数量

        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 交易日天数
        """
        return self.provider.count_trading_days(start_date, end_date)

    def get_previous_trading_day(self, date_str: str = None, n: int = 1) -> str | None:
        """
        获取前一个或前N个交易日

        :param date_str: 起始日期，默认今天
        :param n: 前第N个交易日
        :return: 交易日日期字符串
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        return self.provider.get_next_trading_day(date_str, -n)

    def batch_check(self, date_strs: list[str]) -> dict[str, bool | None]:
        """
        批量检查多个日期是否为交易日

        :param date_strs: 日期列表
        :return: {日期: 是否交易日}
        """
        return self.provider.batch_is_trading_days(date_strs)

    def is_weekend(self, date_str: str) -> bool:
        """
        判断是否为周末

        :param date_str: 日期
        :return: 是否周末
        """
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.weekday() >= 5  # 5=Saturday, 6=Sunday

    def get_weekday_name(self, date_str: str) -> str:
        """获取星期几的中文名称"""
        day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return day_names[dt.weekday()]

    def get_date_range(self, start_date: str, end_date: str,
                       include_weekends: bool = True) -> list[str]:
        """
        获取日期范围内的所有日期

        :param start_date: 开始日期
        :param end_date: 结束日期
        :param include_weekends: 是否包含周末
        :return: 日期字符串列表
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        dates = []
        current = start
        while current <= end:
            if include_weekends or current.weekday() < 5:
                dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        return dates

    def get_month_trading_summary(self, year: int, month: int) -> dict:
        """
        获取某月的交易日汇总信息

        :param year: 年份
        :param month: 月份
        :return: 包含交易日统计的字典
        """
        start = f"{year}-{month:02d}-01"
        if month == 12:
            end = f"{year + 1}-01-01"
        else:
            end = f"{year}-{month + 1:02d}-01"

        # 计算该月最后一天
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        end = f"{year}-{month:02d}-{last_day:02d}"

        trading_days = self.get_trading_days_between(start, end)
        all_days = self.get_date_range(start, end)

        return {
            'year': year,
            'month': month,
            'total_days': len(all_days),
            'trading_days': len(trading_days),
            'weekend_days': len([d for d in all_days if self.is_weekend(d)]),
            'holiday_days': len(all_days) - len(trading_days) - len([d for d in all_days if self.is_weekend(d)]),
            'trading_day_list': trading_days,
        }

    def clear_cache(self):
        """清空缓存"""
        self.provider.clear_cache()


# 便捷函数
def is_trading_day(date_str: str = None, market: str = 'A') -> bool | None:
    """快速函数：判断是否为交易日"""
    service = CalendarService(market=market)
    return service.is_trading_day(date_str)


def get_next_trading_day(date_str: str = None, n: int = 1, market: str = 'A') -> str | None:
    """快速函数：获取 T+N 交易日"""
    service = CalendarService(market=market)
    return service.get_next_trading_day(date_str, n)
