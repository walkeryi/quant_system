# ui/popups/fenshi_popup.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from ui.charts.fenshi_chart import FenshiChart
from ui.threads.fenshi_thread import FenshiDataThread

class FenshiPopup(QDialog):
    def __init__(self, code, date, parent=None):
        super().__init__(parent)
        self.code = code
        self.date = date
        self.setWindowTitle(f"{code} {date} 分时图")
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        self.chart = FenshiChart()
        layout.addWidget(self.chart.canvas)
        self.status_label = QLabel("加载中...")
        layout.addWidget(self.status_label)
        self.load_data()

    def load_data(self):
        self.thread = FenshiDataThread(self.code)
        self.thread.finished.connect(self.on_data_ready)
        self.thread.error.connect(self.on_error)
        self.thread.start()

    def on_data_ready(self, df):
        base = df.attrs.get('base', {})
        if df.empty:
            self.status_label.setText("该日期无分时数据")
            return
        data_date = base.get('date')
        if data_date != self.date:
            self.status_label.setText(f"注意：接口返回的是 {data_date} 的数据")
        self.chart.draw(df, base)
        self.status_label.hide()

    def on_error(self, msg):
        self.status_label.setText(f"获取失败：{msg}")