from PyQt6.QtWidgets import QWidget, QVBoxLayout
from .kline_chart import KlineChart


class KlineChartWidget(QWidget):
    """K线图控件（专注于精准展现日线数据）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart = KlineChart(wrapper=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 直接充满整个布局
        layout.addWidget(self.chart.canvas, stretch=1)

    def update_data(self, df):
        """接收最新的日线数据，并刷新图表"""
        self.chart.draw(df)