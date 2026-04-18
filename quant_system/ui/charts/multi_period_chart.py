# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QWidget, QGridLayout
from .kline_chart_widget import KlineChartWidget

class MultiPeriodChart(QWidget):
    """多周期同列K线图组件"""
    def __init__(self):
        super().__init__()
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.periods = ['5min', '15min', '30min', '60min', '日K']
        self.charts = {}

        # 创建5个周期图表（2行3列，最后一个占位空）
        positions = [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0)]  # 5行2列
        for i, period in enumerate(self.periods):
            row, col = positions[i]
            chart = KlineChartWidget()
            self.charts[period] = chart
            layout.addWidget(chart, row, col)

    def update_data(self, period_data):
        """更新各周期数据
        period_data: dict, key为周期名，value为对应的DataFrame
        """
        for period, df in period_data.items():
            if period in self.charts:
                self.charts[period].update_data(df)