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
    _fenshi_memory_cache = {}

    def __init__(self):
        self.storage = Storage()
        self.stock_list_provider = StockListProvider()
        self.trade_calendar = TradeCalendar()
        self.daily_provider = DailyDataProvider()
        self.fenshi_provider = FenshiDataProvider()
        self.weekly_provider = WeeklyDataProvider()
        self.monthly_provider = MonthlyDataProvider()

    def get_daily_data(self, code: str, start_date: str = None, end_date: str = None, all_data: bool = False):
        """整合后的日线获取逻辑：双轨制缓存"""
        status = self.storage.get_stock_status(code)
        if status == 302:
            return "DELISTED"

        # 判断是否需要全量数据（回测传入日期范围时，强制视为需要全量）
        is_all = all_data or (start_date and end_date)
        suffix = "all" if is_all else "100"

        try:
            # 核心优化：看盘加载 _100.parquet，回测加载 _all.parquet，互不干扰
            cache_path = f"quant_system/cache/daily/{code}_{suffix}.parquet"
            df = None

            if self.storage.is_cache_fresh(cache_path, max_age_days=1):
                df = self.storage.load_parquet(cache_path)

            if df is None or df.empty:
                logger.info(f"缓存失效或过期，向 daily API 请求数据: {code} (获取={'全量' if is_all else '100笔'})")
                df = self.daily_provider.fetch(code, all_data=is_all)

                if df is not None and not df.empty:
                    ret_code = getattr(df, 'ret', 200)
                    if hasattr(df, 'attrs'):
                        ret_code = df.attrs.get('ret', ret_code)

                    if ret_code == 302:
                        self.storage.update_stock_status(code, 302)
                        return "DELISTED"

                    self.storage.save_parquet(df, cache_path)

            # 回测时如果传了起止时间，在这里进行精准截取
            if df is not None and not df.empty and start_date and end_date:
                mask = (df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))
                return df.loc[mask]

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
        status = self.storage.get_stock_status(code)
        if status == 302:
            return "DELISTED"

        try:
            code = str(code).zfill(6)
            cached_df = DataPreprocessor._fenshi_memory_cache.get(code)

            if cached_df is None:
                result = self.fenshi_provider.fetch(code, fetch_all=True)
            else:
                result = self.fenshi_provider.fetch(code, fetch_all=False)

            ret_code = getattr(result, 'ret', 200)
            if hasattr(result, 'attrs'):
                ret_code = result.attrs.get('ret', ret_code)

            if ret_code == 302 or (isinstance(result, str) and "302" in result):
                self.storage.update_stock_status(code, 302)
                return "DELISTED"

            if result is None or result.empty:
                return cached_df

            if cached_df is None:
                DataPreprocessor._fenshi_memory_cache[code] = result
                return result

            combined = (
                pd.concat([cached_df, result], ignore_index=True)
                .drop_duplicates(subset=['time'], keep='last')
                .sort_values(by='time')
                .reset_index(drop=True)
            )
            combined.attrs['base'] = result.attrs.get('base', cached_df.attrs.get('base', {}))
            DataPreprocessor._fenshi_memory_cache[code] = combined
            return combined
        except Exception as e:
            if "302" in str(e):
                self.storage.update_stock_status(code, 302)
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