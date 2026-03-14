import os
import pandas as pd
from datetime import datetime
from .utils import setup_logger

logger = setup_logger(__name__)

class Storage:
    @staticmethod
    def save_csv(df, file_path):
        """保存 DataFrame 到 CSV，编码使用 utf-8-sig 以兼容 Excel"""
        try:
            df.to_csv(file_path, encoding='utf-8-sig', index=False)
            return True
        except Exception as e:
            logger.error(f"保存失败 {file_path}: {e}")
            return False

    @staticmethod
    def load_csv(file_path, dtype={'code': str}):
        """读取 CSV，默认不使用第一列作为索引，确保 code 列存在"""
        try:
            if os.path.exists(file_path):
                return pd.read_csv(file_path, encoding='utf-8-sig', dtype=dtype)
            return None
        except Exception as e:
            logger.error(f"加载失败 {file_path}: {e}")
            return None