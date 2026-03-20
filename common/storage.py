import os
import pandas as pd
from .utils import setup_logger
from datetime import datetime, timedelta

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
    def load_csv(file_path, **kwargs):
        """读取 CSV，支持传递任意参数给 pd.read_csv"""
        try:
            if os.path.exists(file_path):
                # 默认将 code 列视为字符串
                if 'dtype' not in kwargs:
                    kwargs['dtype'] = {'code': str}
                return pd.read_csv(file_path, encoding='utf-8-sig', **kwargs)
            return None
        except Exception as e:
            logger.error(f"加载失败 {file_path}: {e}")
            return None

    @staticmethod
    def is_cache_fresh(file_path, max_age_days=7):
        """检查缓存文件是否在指定天数内生成"""
        if not os.path.exists(file_path):
            return False
        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        return datetime.now() - file_time < timedelta(days=max_age_days)