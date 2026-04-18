# -*- coding: utf-8 -*-
"""
K线图 widget
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QButtonGroup
from PyQt6.QtCore import pyqtSignal
from .kline_chart import KlineChart


class KlineChartWidget(QWidget):
    period_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart = KlineChart(wrapper=self)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_panel = QWidget()
        top_panel.setMaximumHeight(35)
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(10, 5, 10, 0)
        top_layout.setSpacing(10)

        self.btn_daily = QPushButton("日线")
        self.btn_weekly = QPushButton("周线")
        self.btn_monthly = QPushButton("月线")

        self.btn_daily.setCheckable(True)
        self.btn_weekly.setCheckable(True)
        self.btn_monthly.setCheckable(True)
        self.btn_daily.setChecked(True)

        btn_style = """
            QPushButton { background-color: #333; color: #ccc; border: none; padding: 4px 15px; border-radius: 3px; font-size: 13px;}
            QPushButton:checked { background-color: #2196F3; color: white; font-weight: bold; }
        """
        self.btn_daily.setStyleSheet(btn_style)
        self.btn_weekly.setStyleSheet(btn_style)
        self.btn_monthly.setStyleSheet(btn_style)

        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.btn_daily, 1)
        self.btn_group.addButton(self.btn_weekly, 2)
        self.btn_group.addButton(self.btn_monthly, 3)
        self.btn_group.idClicked.connect(self.on_btn_clicked)

        top_layout.addWidget(self.btn_daily)
        top_layout.addWidget(self.btn_weekly)
        top_layout.addWidget(self.btn_monthly)
        top_layout.addStretch()

        main_layout.addWidget(top_panel, stretch=0)
        main_layout.addWidget(self.chart.canvas, stretch=1)

    def on_btn_clicked(self, btn_id):
        if btn_id == 1:
            period = 'daily'
        elif btn_id == 2:
            period = 'weekly'
        else:
            period = 'monthly'
        self.period_changed.emit(period)

    def update_data(self, df, period='daily'):
        self.chart.draw(df, period)
