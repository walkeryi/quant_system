# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from .fenshi_volume_chart import FenshiVolumeChart

class FenshiVolumeChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart = FenshiVolumeChart()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chart.canvas)

    def update_data(self, df):
        self.chart.draw(df)

    def set_width_stage(self, stage):
        if not self.parentWidget(): return
        stages = [0.5, 0.75, 1.0]
        # 减去价格图侧边栏的 20px 以对齐画布
        target_w = int(self.parentWidget().width() * stages[stage]) - 20
        self.setFixedWidth(target_w)

    def sync_crosshair(self, x_idx):
        self.chart.update_crosshair_sync(x_idx)

    def hide_crosshair(self):
        self.chart.hide_crosshair()