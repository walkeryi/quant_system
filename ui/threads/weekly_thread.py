# ui/threads/weekly_thread.py
from PyQt6.QtCore import QThread, pyqtSignal
import pandas as pd
from data_preprocessing.weekly import WeeklyDataProvider

class WeeklyDataThread(QThread):
    finished = pyqtSignal(pd.DataFrame)
    error = pyqtSignal(str)

    def __init__(self, code, parent=None):
        super().__init__(parent)
        self.code = code
        self.provider = WeeklyDataProvider()

    def run(self):
        try:
            df = self.provider.fetch(self.code)
            if df is not None and not df.empty:
                self.finished.emit(df)
            else:
                self.error.emit("未获取到周线数据或数据为空")
        except Exception as e:
            self.error.emit(str(e))