# ui/charts/fenshi_chart_widget.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QPoint
from .fenshi_chart import FenshiChart


class FenshiChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart = FenshiChart()
        self.width_stage = 2  # 0:50%, 1:75%, 2:100%
        self.height_is_custom = False
        self.is_resizing_v = False
        self.start_y = 0
        self.start_h = 0

        # 主布局使用水平排列：左侧图表 + 右侧操作杆
        layout = QHBoxLayout(self)
        # 【关键修复】：设置底部 8px 边距，作为专门的高度拉伸感应区
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(0)

        # 1. 添加画布
        layout.addWidget(self.chart.canvas, stretch=1)

        # 2. 右侧操作栏（用于分级调整宽度）
        self.side_bar = QWidget()
        self.side_bar.setFixedWidth(20)
        self.side_bar.setStyleSheet("background-color: #252525; border-left: 1px solid #444;")
        side_layout = QVBoxLayout(self.side_bar)
        side_layout.setContentsMargins(0, 0, 0, 0)

        self.toggle_btn = QPushButton("◀")
        self.toggle_btn.setFixedSize(20, 80)
        self.toggle_btn.setStyleSheet("""
            QPushButton { color: #aaa; border: none; background: #333; font-weight: bold; }
            QPushButton:hover { background: #444; color: white; }
        """)
        self.toggle_btn.clicked.connect(self.rotate_width_stage)
        side_layout.addWidget(self.toggle_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.side_bar)

        self.setMouseTracking(True)

    def rotate_width_stage(self):
        """三档循环切换：50% -> 75% -> 100%"""
        self.width_stage = (self.width_stage + 1) % 3
        # 档位 2 (100%) 时箭头向左，其余向右
        self.toggle_btn.setText("◀" if self.width_stage == 2 else "▶")
        self.apply_size()

    def apply_size(self):
        """同步宽度比例"""
        if not self.parentWidget(): return
        stages = [0.5, 0.75, 1.0]
        # 基于父容器宽度计算本控件宽度
        target_w = int(self.parentWidget().width() * stages[self.width_stage])
        self.setFixedWidth(target_w)

    def mousePressEvent(self, event):
        # 如果在底部 8 像素感应区按下
        if event.pos().y() >= self.height() - 8:
            self.is_resizing_v = True
            self.start_y = event.globalPosition().y()
            self.start_h = self.height()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # 改变鼠标指针为上下拉伸样式
        if event.pos().y() >= self.height() - 8 or self.is_resizing_v:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        if self.is_resizing_v:
            diff = event.globalPosition().y() - self.start_y
            self.setFixedHeight(max(150, int(self.start_h + diff)))
            self.height_is_custom = True
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.is_resizing_v = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def update_data(self, df, base):
        self.chart.draw(df, base)