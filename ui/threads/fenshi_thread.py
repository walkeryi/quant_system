from PyQt6.QtCore import QThread, pyqtSignal
from data_preprocessing import DataPreprocessor

class FenshiDataThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, code):
        super().__init__()
        self.code = code

    def run(self):
        try:
            dp = DataPreprocessor()
            df = dp.get_fenshi_data(self.code)
            if df is None or df.empty:
                self.error.emit("无法获取分时数据")
                return
            self.finished.emit(df)
        except Exception as e:
            self.error.emit(str(e))