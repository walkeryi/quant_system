# -*- coding: utf-8 -*-
"""
股票列表数据加载线程
"""
import logging
from PyQt6.QtCore import QThread, pyqtSignal
from quant_system.services import DataPreprocessor

logger = logging.getLogger('quant_system')


class StockListThread(QThread):
    finished = pyqtSignal(object, str)
    error = pyqtSignal(str)

    def __init__(self, use_cache):
        super().__init__()
        self.use_cache = use_cache

    def run(self):
        try:
            dp = DataPreprocessor()
            result = dp.get_stock_list(use_cache=self.use_cache)
            if isinstance(result, tuple) and len(result) == 2:
                df, update_date = result
            else:
                df = result
                update_date = ""
            self.finished.emit(df, update_date)
        except Exception as e:
            logger.exception("StockListThread 异常")
            self.error.emit(str(e))
