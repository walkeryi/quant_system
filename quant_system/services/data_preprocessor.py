# -*- coding: utf-8 -*-
"""
数据预处理服务
整合所有数据 provider，提供统一的数据获取接口
"""
import logging
import pandas as pd
from quant_system.data.providers import (
    StockListProvider,
    DailyDataProvider,
    FenshiDataProvider,
    WeeklyDataProvider,
    MonthlyDataProvider,
)
from quant_system.data.storage import Storage

logger = logging.getLogger('quant_system')


class DataPreprocessor:
    _fenshi_memory_cache = {}

    def __init__(self):
        self.storage = Storage()
        self.stock_list_provider = StockListProvider()
        self.daily_provider = DailyDataProvider()
        self.fenshi_provider = FenshiDataProvider()
        self.weekly_provider = WeeklyDataProvider()
        self.monthly_provider = MonthlyDataProvider()

    def get_daily_data(self, code: str, start_date: str = None, end_date: str = None, all_data: bool = False):
        """整合后的日线获取逻辑：双轨制缓存"""
        status = self.storage.get_stock_status(code)
        if status == 302:
            return "DELISTED"

        is_all = all_data or (start_date and end_date)
        suffix = "all" if is_all else "100"

        try:
            cache_path = f"quant_system/cache/daily/{code}_{suffix}.parquet"
            df = None

            if self.storage.is_cache_fresh(cache_path, max_age_days=1):
                df = self.storage.load_parquet(cache_path)

            if df is None or df.empty:
                logger.info(f"缓存失效或过期，向 daily API 请求数据: {code} (获取={'全量' if is_all else '100笔'})")
                df = self.daily_provider.fetch(code, all_data=is_all)

                if df is not None and not df.empty:
                    ret_code = df.attrs.get('ret', 200)
                    if ret_code == 302:
                        self.storage.update_stock_status(code, 302)
                        return "DELISTED"
                    self.storage.save_parquet(df, cache_path)

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
                    ret_code = df.attrs.get('ret', 200)
                    if ret_code == 302:
                        self.storage.update_stock_status(code, 302)
                        return "DELISTED"
                    self.storage.save_parquet(df, cache_path)

            return df
        except Exception as e:
            logger.exception(f"获取 {cache_type} 数据异常: {code}")
            return None

    def get_weekly_data(self, code: str):
        return self._get_kline_data_logic(code, self.weekly_provider, "weekly")

    def get_monthly_data(self, code: str):
        return self._get_kline_data_logic(code, self.monthly_provider, "monthly")

    def get_stock_list(self, use_cache: bool = True):
        try:
            return self.stock_list_provider.fetch(use_cache=use_cache)
        except Exception as e:
            logger.exception("get_stock_list 异常")
            return None, None

    def get_fenshi_data(self, code: str):
        status = self.storage.get_stock_status(code)
        if status == 302:
            return "DELISTED"

        try:
            code = str(code).zfill(6)
            cached_df = DataPreprocessor._fenshi_memory_cache.get(code)
            logger.info(f"[Preprocessor] code={code} cached_df={'None' if cached_df is None else f'cols={list(cached_df.columns)} rows={len(cached_df)}'}")

            if cached_df is None:
                result = self.fenshi_provider.fetch(code, fetch_all=True)
            else:
                result = self.fenshi_provider.fetch(code, fetch_all=False)

            logger.info(f"[Preprocessor] code={code} result type={type(result).__name__} "
                        f"is_df={isinstance(result, pd.DataFrame)} "
                        f"is_str={isinstance(result, str)}")

            if not isinstance(result, pd.DataFrame):
                logger.warning(f"[Preprocessor] code={code} result 不是 DataFrame，返回缓存: {cached_df is not None}")
                return cached_df if cached_df is not None else result

            logger.info(f"[Preprocessor] code={code} result cols={list(result.columns)} rows={len(result)} "
                        f"ret_code={result.attrs.get('ret', 'N/A')}")

            ret_code = result.attrs.get('ret', 200)

            if ret_code == 302 or (isinstance(result, str) and "302" in result):
                self.storage.update_stock_status(code, 302)
                return "DELISTED"

            if result.empty:
                logger.warning(f"[Preprocessor] code={code} result 为空，返回缓存: {cached_df is not None}")
                return cached_df if cached_df is not None else result

            if cached_df is None:
                DataPreprocessor._fenshi_memory_cache[code] = result
                logger.info(f"[Preprocessor] code={code} 无缓存，直接缓存并返回")
                return result

            if 'time' in cached_df.columns and 'time' in result.columns:
                combined = (
                    pd.concat([cached_df, result], ignore_index=True)
                    .drop_duplicates(subset=['time'], keep='last')
                    .sort_values(by='time')
                    .reset_index(drop=True)
                )
                logger.info(f"[Preprocessor] code={code} 合并缓存+新数据: {len(cached_df)}+{len(result)}={len(combined)}")
            else:
                combined = result
                logger.warning(f"[Preprocessor] code={code} 列不一致，用新数据覆盖: cached={list(cached_df.columns)} result={list(result.columns)}")
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
