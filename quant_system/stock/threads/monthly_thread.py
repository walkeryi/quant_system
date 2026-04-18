# -*- coding: utf-8 -*-
"""
月线数据加载线程
"""
from PyQt6.QtCore import QThread, pyqtSignal
from quant_system.services import DataPreprocessor


class MonthlyDataThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, code, parent=None):
        super().__init__(parent)
        self.code = code

    def run(self):
        try:
            dp = DataPreprocessor()
            df = dp.get_monthly_data(self.code)

            if isinstance(df, str) and df == "DELISTED":
                self.error.emit("该股票已退市")
            elif df is not None and not df.empty:
                self.finished.emit(df)
            else:
                self.error.emit("未获取到月线数据")
        except Exception as e:
            self.error.emit(str(e))
