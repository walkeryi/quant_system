from PyQt6.QtWidgets import QWidget, QVBoxLayout
from .kline_chart import KlineChart

class KlineChartWidget(QWidget):
    """K线图控件，包含一个KlineChart画布"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart = KlineChart()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chart.canvas)

    def update_data(self, df):
        self.chart.draw(df)