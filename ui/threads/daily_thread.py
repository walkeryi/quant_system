from PyQt6.QtCore import QThread, pyqtSignal
from data_preprocessing import DataPreprocessor

class DailyDataThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, code):
        super().__init__()
        self.code = code

    def run(self):
        try:
            dp = DataPreprocessor()
            # 将 all_data 改为 False，只获取最新 100 条日线数据
            df = dp.get_daily_data(self.code, all_data=False)

            if isinstance(df, str) and df == "DELISTED":
                self.error.emit("302_DELISTED")
                return

            if df is None or df.empty:
                self.error.emit("无法获取日线数据")
                return
            self.finished.emit(df)
        except Exception as e:
            if "302" in str(e):
                self.error.emit("302_DELISTED")
            else:
                self.error.emit(str(e))