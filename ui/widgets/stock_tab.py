import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QHeaderView,
                             QMessageBox, QTabWidget, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.charts.fenshi_chart_widget import FenshiChartWidget
from ui.charts.fenshi_volume_chart_widget import FenshiVolumeChartWidget
from ui.threads.fenshi_thread import FenshiDataThread
from ui.charts.kline_chart_widget import KlineChartWidget
from ui.threads.daily_thread import DailyDataThread


class StockTab(QWidget):
    switch_requested = pyqtSignal(int)

    def __init__(self, code, parent=None):
        super().__init__(parent)
        self.code = code
        self.base_info = {}
        self.fenshi_loaded = False
        self.kline_loaded = False
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # ========== 1. 数据面板 (10个字段) ==========
        data_panel = QWidget(); data_panel.setMaximumHeight(160)
        data_layout = QHBoxLayout(data_panel)
        left_widget = QWidget(); left_layout = QVBoxLayout(left_widget)
        self.code_label = QLabel(self.code); self.code_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.name_label = QLabel("--"); self.name_label.setStyleSheet("font-size: 18px; color: gray;")
        left_layout.addWidget(self.code_label); left_layout.addWidget(self.name_label); left_layout.addStretch()

        btn_widget = QWidget(); btn_layout = QHBoxLayout(btn_widget)
        self.prev_btn = QPushButton("◀"); self.next_btn = QPushButton("▶")
        self.prev_btn.setFixedSize(40,40); self.next_btn.setFixedSize(40,40)
        self.prev_btn.clicked.connect(lambda: self.switch_requested.emit(-1))
        self.next_btn.clicked.connect(lambda: self.switch_requested.emit(1))
        btn_layout.addWidget(self.prev_btn); btn_layout.addWidget(self.next_btn)

        right_widget = QWidget(); right_layout = QGridLayout(right_widget); self.labels = {}
        fields = [('date','日期'),('open','开盘'),('high','最高'),('low','最低'),('close','昨收'),('振幅','振幅(%)'),('pe','市盈率'),('pb','市净率'),('mkt_cap','市值(万)'),('nwb','内外比')]
        for i, (key, desc) in enumerate(fields):
            row, col = divmod(i, 2)
            right_layout.addWidget(QLabel(f"{desc}:"), row, col*2)
            val_lbl = QLabel("--"); val_lbl.setStyleSheet("font-weight: bold; color: #eee;")
            right_layout.addWidget(val_lbl, row, col*2+1); self.labels[key] = val_lbl

        data_layout.addWidget(left_widget, 1); data_layout.addWidget(btn_widget, 0); data_layout.addWidget(right_widget, 2)
        main_layout.addWidget(data_panel)

        # ========== 2. 图表面板 (垂直排列) ==========
        self.tab_widget = QTabWidget()
        fenshi_page = QWidget(); fenshi_layout = QVBoxLayout(fenshi_page)
        fenshi_layout.setContentsMargins(0,0,0,0); fenshi_layout.setSpacing(0)

        self.fenshi_price_widget = FenshiChartWidget()
        self.fenshi_volume_widget = FenshiVolumeChartWidget()

        # 【核心】：连接宽度联动和十字光标同步信号
        self.fenshi_price_widget.widthStageChanged.connect(self.fenshi_volume_widget.set_width_stage)
        self.fenshi_price_widget.crosshairSyncSignal.connect(self.on_fenshi_crosshair_sync)

        fenshi_layout.addWidget(self.fenshi_price_widget, stretch=3)
        fenshi_layout.addWidget(self.fenshi_volume_widget, stretch=1)
        fenshi_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.tab_widget.addTab(fenshi_page, "分时图")

        self.kline_widget = KlineChartWidget()
        self.tab_widget.addTab(self.kline_widget, "K线图")
        main_layout.addWidget(self.tab_widget)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def on_fenshi_crosshair_sync(self, x_idx):
        if x_idx == -1: self.fenshi_volume_widget.hide_crosshair()
        else: self.fenshi_volume_widget.sync_crosshair(x_idx)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'fenshi_price_widget'):
            self.fenshi_price_widget.apply_size()
            self.fenshi_volume_widget.set_width_stage(self.fenshi_price_widget.width_stage)
            if not self.fenshi_price_widget.height_is_custom:
                self.fenshi_price_widget.setFixedHeight(int(self.height() * 0.6))

    def on_fenshi_ready(self, df):
        self.fenshi_loaded = True
        base = df.attrs.get('base', {})
        self.base_info.update(base)
        self.update_data_panel(self.base_info)
        self.fenshi_price_widget.update_data(df, base)
        self.fenshi_volume_widget.update_data(df)

    def update_data_panel(self, base):
        self.name_label.setText(base.get('name', '--'))
        self.labels['date'].setText(base.get('date', '--'))
        def fmt(key):
            val = base.get(key, 0)
            return f"{float(val):.2f}" if val else "--"
        self.labels['open'].setText(fmt('KaiPan')); self.labels['high'].setText(fmt('ZuiGao'))
        self.labels['low'].setText(fmt('ZuiDi')); self.labels['close'].setText(fmt('ZuoShou'))
        self.labels['振幅'].setText(f"{base.get('ZhenFu', '--')}%")
        self.labels['pe'].setText(fmt('ShiYingLv')); self.labels['pb'].setText(fmt('ShiJingLv'))
        self.labels['mkt_cap'].setText(f"{base.get('ShiZhi', 0):,.0f}")
        self.labels['nwb'].setText(fmt('NeiWaiBi'))

    def on_tab_changed(self, index):
        if index == 0 and not self.fenshi_loaded:
            self.load_fenshi_data()
        elif index == 1 and not self.kline_loaded:
            self.load_kline_data()

    def load_fenshi_data(self):
        self.thread = FenshiDataThread(self.code)
        self.thread.finished.connect(self.on_fenshi_ready); self.thread.start()

# 5. 新增：拉取 K 线数据的逻辑与回调
    def load_kline_data(self):
        self.kline_thread = DailyDataThread(self.code)
        self.kline_thread.finished.connect(self.on_kline_ready)
        self.kline_thread.error.connect(lambda e: QMessageBox.warning(self, "数据错误", f"加载K线数据失败: {e}"))
        self.kline_thread.start()

    def on_kline_ready(self, df):
        self.kline_loaded = True
        self.kline_widget.update_data(df)