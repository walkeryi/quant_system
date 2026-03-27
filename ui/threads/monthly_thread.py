# quant_system/ui/threads/monthly_thread.py
from PyQt6.QtCore import QThread, pyqtSignal
import pandas as pd
from data_preprocessing.fetcher import DataPreprocessor

class MonthlyDataThread(QThread):
    finished = pyqtSignal(object)  # 修复：使用 object 安全传递 DataFrame
    error = pyqtSignal(str)

    def __init__(self, code, parent=None):
        super().__init__(parent)
        self.code = code
        self.preprocessor = DataPreprocessor()

    def run(self):
        try:
            df = self.preprocessor.get_monthly_data(self.code)
            # 核心修复：必须先判断类型，防止 DataFrame 与字符串直接比对造成 ambiguous 报错崩溃
            if isinstance(df, str) and df == "DELISTED":
                self.error.emit("该股票已退市")
            elif df is not None and not df.empty:
                self.finished.emit(df)
            else:
                self.error.emit("未获取到月线数据")
        except Exception as e:
            self.error.emit(str(e))