# stock_list_thread.py
import logging
from PyQt6.QtCore import QThread, pyqtSignal
from data_preprocessing.fetcher import DataPreprocessor

logger = logging.getLogger('quant_system')

class StockListThread(QThread):
    finished = pyqtSignal(object, str)  # DataFrame, update_date
    error = pyqtSignal(str)

    def __init__(self, use_cache):
        super().__init__()
        self.use_cache = use_cache

    def run(self):
        try:
            dp = DataPreprocessor()
            result = dp.get_stock_list(use_cache=self.use_cache)
            # 兼容单返回值（DataFrame）和可能的元组返回值
            if isinstance(result, tuple) and len(result) == 2:
                df, update_date = result
            else:
                df = result
                update_date = ""  # 如果没有更新日期，留空
            self.finished.emit(df, update_date)
        except Exception as e:
            logger.exception("StockListThread 异常")
            self.error.emit(str(e))