# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from .fenshi_chart import FenshiChart

class FenshiChartWidget(QWidget):
    widthStageChanged = pyqtSignal(int)
    crosshairSyncSignal = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart = FenshiChart(wrapper=self)
        self.width_stage = 2
        self.height_is_custom = False
        self.is_resizing_v = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8); layout.setSpacing(0)
        layout.addWidget(self.chart.canvas)

        self.side_bar = QWidget(); self.side_bar.setFixedWidth(20)
        self.side_bar.setStyleSheet("background-color: #252525; border-left: 1px solid #444;")
        side_layout = QVBoxLayout(self.side_bar)
        self.toggle_btn = QPushButton("◀")
        self.toggle_btn.setFixedSize(20, 80); self.toggle_btn.clicked.connect(self.rotate_width_stage)
        self.toggle_btn.setStyleSheet("color: #aaa; border: none; background: #333; font-weight: bold;")
        side_layout.addWidget(self.toggle_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.side_bar)
        self.setMouseTracking(True)

    def rotate_width_stage(self):
        self.width_stage = (self.width_stage + 1) % 3
        self.toggle_btn.setText("◀" if self.width_stage == 2 else "▶")
        self.apply_size()
        self.widthStageChanged.emit(self.width_stage)

    def apply_size(self):
        if not self.parentWidget(): return
        stages = [0.5, 0.75, 1.0]
        self.setFixedWidth(int(self.parentWidget().width() * stages[self.width_stage]))

    def mousePressEvent(self, event):
        if event.pos().y() >= self.height() - 8:
            self.is_resizing_v = True; self.start_y = event.globalPosition().y(); self.start_h = self.height()

    def mouseMoveEvent(self, event):
        if event.pos().y() >= self.height() - 8 or self.is_resizing_v:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else: self.setCursor(Qt.CursorShape.ArrowCursor)
        if self.is_resizing_v:
            diff = event.globalPosition().y() - self.start_y
            self.setFixedHeight(max(150, int(self.start_h + diff))); self.height_is_custom = True

    def mouseReleaseEvent(self, event): self.is_resizing_v = False
    def update_data(self, df, base): self.chart.draw(df, base)