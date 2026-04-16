# quant_system/common/storage.py
import os
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from .utils import setup_logger

logger = setup_logger(__name__)

class Storage:
    # --- 缓存时效检查 (修复 daily.py 的报错) ---
    @staticmethod
    def is_cache_fresh(file_path, max_age_days=1):
        """检查缓存文件是否在有效期内"""
        if not os.path.exists(file_path):
            return False
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        return (datetime.now() - file_mtime) < timedelta(days=max_age_days)

    # --- CSV 存储 (兼容 daily.py 原有的缓存逻辑) ---
    @staticmethod
    def save_csv(df, file_path):
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            df.to_csv(file_path, index=False)
            return True
        except Exception as e:
            logger.error(f"CSV 保存失败 {file_path}: {e}")
            return False

    @staticmethod
    def load_csv(file_path):
        if os.path.exists(file_path):
            try:
                return pd.read_csv(file_path)
            except Exception as e:
                logger.error(f"CSV 加载失败 {file_path}: {e}")
        return None

    # --- 高性能二进制存储 (Parquet) ---
    @staticmethod
    def save_parquet(df, file_path):
        """使用 Parquet 存储，支持 Snappy 压缩，读取速度远超 CSV"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            df.to_parquet(file_path, compression='snappy', index=True)
            return True
        except Exception as e:
            logger.error(f"Parquet 保存失败 {file_path}: {e}")
            return False

    @staticmethod
    def load_parquet(file_path):
        """从 Parquet 文件加载数据，实现近乎瞬时的 I/O"""
        if os.path.exists(file_path):
            try:
                return pd.read_parquet(file_path)
            except Exception as e:
                logger.error(f"Parquet 加载失败 {file_path}: {e}")
        return None

    # --- 数据库状态管理 (处理 302 退市等返回码) ---
    @staticmethod
    def update_stock_status(code, status_code):
        """在本地数据库记录股票状态，实现无效代码的快速过滤"""
        db_path = "quant_system/cache/metadata.db"
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS stock_status 
                              (code TEXT PRIMARY KEY, status INTEGER, last_update TEXT)''')
            cursor.execute("REPLACE INTO stock_status VALUES (?, ?, ?)",
                           (code, status_code, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"更新数据库状态失败: {e}")

    @staticmethod
    def get_stock_status(code):
        """检查股票是否为 302 已退市状态"""
        db_path = "quant_system/cache/metadata.db"
        if not os.path.exists(db_path):
            return 200
        try:
            conn = sqlite3.connect(db_path)
            res = conn.execute("SELECT status FROM stock_status WHERE code=?", (code,)).fetchone()
            conn.close()
            status = res[0] if res else 200
            if status == 302:
                logger.info(f"拦截退市股票请求: code={code}, status=302")
            return status
        except Exception as e:
            logger.error(f"读取股票状态失败，默认放行: code={code}, err={e}")
            return 200