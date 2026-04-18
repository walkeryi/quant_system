# -*- coding: utf-8 -*-
"""
文件缓存管理 - Parquet/CSV + 状态管理
"""
import os
import sqlite3
import time
import pandas as pd
from datetime import datetime, timedelta
from quant_system.config import BASE_DIR


class Storage:
    """统一文件缓存管理 + 股票状态管理"""

    @staticmethod
    def _get_path(relative_path: str) -> str:
        if os.path.isabs(relative_path):
            return relative_path
        return os.path.join(BASE_DIR, relative_path)

    @staticmethod
    def save_parquet(df: pd.DataFrame, relative_path: str):
        path = Storage._get_path(relative_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_parquet(path, compression='snappy', index=True)

    @staticmethod
    def load_parquet(relative_path: str) -> pd.DataFrame | None:
        path = Storage._get_path(relative_path)
        if not os.path.exists(path):
            return None
        try:
            return pd.read_parquet(path)
        except Exception:
            return None

    @staticmethod
    def save_csv(df: pd.DataFrame, relative_path: str):
        path = Storage._get_path(relative_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=False)

    @staticmethod
    def load_csv(relative_path: str) -> pd.DataFrame | None:
        path = Storage._get_path(relative_path)
        if not os.path.exists(path):
            return None
        try:
            return pd.read_csv(path)
        except Exception:
            return None

    @staticmethod
    def is_cache_fresh(relative_path: str, max_age_days: int = 1) -> bool:
        path = Storage._get_path(relative_path)
        if not os.path.exists(path):
            return False
        file_mtime = datetime.fromtimestamp(os.path.getmtime(path))
        return (datetime.now() - file_mtime) < timedelta(days=max_age_days)

    @staticmethod
    def update_stock_status(code, status_code):
        """在本地数据库记录股票状态"""
        db_path = Storage._get_path("quant_system/cache/metadata.db")
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS stock_status
                              (code TEXT PRIMARY KEY, status INTEGER, last_update TEXT)''')
            cursor.execute("REPLACE INTO stock_status VALUES (?, ?, ?)",
                           (code, status_code, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            conn.close()
        except Exception:
            pass

    @staticmethod
    def get_stock_status(code):
        """检查股票是否为退市状态"""
        db_path = Storage._get_path("quant_system/cache/metadata.db")
        if not os.path.exists(db_path):
            return 200
        try:
            conn = sqlite3.connect(db_path)
            res = conn.execute("SELECT status FROM stock_status WHERE code=?", (code,)).fetchone()
            conn.close()
            return res[0] if res else 200
        except Exception:
            return 200
