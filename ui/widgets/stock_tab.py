# ui/widgets/stock_tab.py
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QHeaderView,
                             QMessageBox, QTabWidget, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.charts.fenshi_chart_widget import FenshiChartWidget
from ui.charts.kline_chart_widget import KlineChartWidget
from ui.threads.fenshi_thread import FenshiDataThread
from ui.threads.daily_thread import DailyDataThread
from ui.popups.fenshi_popup import FenshiPopup
from ui.helpers.daily_helpers import fill_daily_table, save_fenshi_csv

logger = logging.getLogger('quant_system')


class StockTab(QWidget):
    """单个股票的标签页，包含数据面板和图表面板（分时/K线）"""
    switch_requested = pyqtSignal(int)  # delta: -1 上一个, +1 下一个

    def __init__(self, code, parent=None):
        super().__init__(parent)
        self.code = code
        self.daily_df = None
        self.base_info = {}
        self.fenshi_loaded = False
        self.kline_loaded = False
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # ========== 数据面板 ==========
        data_panel = QWidget()
        data_panel.setMaximumHeight(160)
        data_layout = QHBoxLayout(data_panel)

        # 左侧：股票代码和名称
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.code_label = QLabel(self.code)
        self.code_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.name_label = QLabel("--")
        self.name_label.setStyleSheet("font-size: 18px; color: gray;")
        left_layout.addWidget(self.code_label)
        left_layout.addWidget(self.name_label)
        left_layout.addStretch()

        # 中间：切换股票按钮
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(40, 40)
        self.prev_btn.clicked.connect(lambda: self.switch_requested.emit(-1))
        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(40, 40)
        self.next_btn.clicked.connect(lambda: self.switch_requested.emit(1))
        btn_layout.addWidget(self.prev_btn)
        btn_layout.addWidget(self.next_btn)

        # 右侧：基本信息网格
        right_widget = QWidget()
        right_layout = QGridLayout(right_widget)
        self.labels = {}
        fields = [
            ('date', '日期'), ('open', '开盘'), ('high', '最高'), ('low', '最低'),
            ('close', '昨收'), ('振幅', '振幅(%)'), ('内外比', '内外比'),
            ('pe', '市盈率'), ('pb', '市净率'), ('mkt_cap', '市值(万)')
        ]
        for i, (key, desc) in enumerate(fields):
            row, col = divmod(i, 2)
            right_layout.addWidget(QLabel(f"{desc}:"), row, col * 2)
            val_lbl = QLabel("--")
            val_lbl.setStyleSheet("font-weight: bold;")
            right_layout.addWidget(val_lbl, row, col * 2 + 1)
            self.labels[key] = val_lbl

        data_layout.addWidget(left_widget, 1)
        data_layout.addWidget(btn_widget, 0)
        data_layout.addWidget(right_widget, 2)
        main_layout.addWidget(data_panel)

        # ========== 图表面板 ==========
        self.tab_widget = QTabWidget()

        # 为分时图创建一个容器页面，以便支持 AlignLeft 布局
        fenshi_page = QWidget()
        fenshi_page_layout = QVBoxLayout(fenshi_page)
        fenshi_page_layout.setContentsMargins(0, 0, 0, 0)

        self.fenshi_widget = FenshiChartWidget()
        fenshi_page_layout.addWidget(self.fenshi_widget)
        # 【修复对齐】：确保宽度变小时，控件停留在左侧
        fenshi_page_layout.setAlignment(self.fenshi_widget, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.tab_widget.addTab(fenshi_page, "分时图")
        # K线图
        self.kline_widget = KlineChartWidget()
        self.kline_table = QTableWidget()
        self.kline_table.setColumnCount(5)
        self.kline_table.setHorizontalHeaderLabels(["日期", "收盘", "均价", "成交量", "涨幅"])
        self.kline_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        kline_page = QWidget()
        kl_layout = QVBoxLayout(kline_page)
        kl_layout.addWidget(self.kline_widget, stretch=3)
        kl_layout.addWidget(self.kline_table, stretch=2)
        self.tab_widget.addTab(kline_page, "K线图")

        # 【修复】：将 tab_widget 添加到主布局中，否则图表不会显示
        main_layout.addWidget(self.tab_widget)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'fenshi_widget'):
            # 【修复】：统一调用 apply_size 方法，匹配 FenshiChartWidget 的定义
            self.fenshi_widget.apply_size()

            # 2. 初始高度自适应 (如果用户还没手动调整过高度)
            if not self.fenshi_widget.height_is_custom:
                target_height = int(self.height() * 0.6)
                self.fenshi_widget.setFixedHeight(target_height)

    def on_tab_changed(self, index):
        if index == 0 and not self.fenshi_loaded:
            self.load_fenshi_data()
        elif index == 1 and not self.kline_loaded:
            self.load_kline_data()

    def load_fenshi_data(self):
        self.thread = FenshiDataThread(self.code)
        self.thread.finished.connect(self.on_fenshi_ready)
        self.thread.error.connect(self.on_error)
        self.thread.start()

    def load_kline_data(self):
        self.thread = DailyDataThread(self.code)
        self.thread.finished.connect(self.on_kline_ready)
        self.thread.error.connect(self.on_error)
        self.thread.start()

    def on_fenshi_ready(self, df):
        self.fenshi_loaded = True
        base = df.attrs.get('base', {})
        self.fenshi_widget.update_data(df, base)

    def on_kline_ready(self, df):
        self.kline_loaded = True
        if df.empty: return
        self.daily_df = df
        if self.base_info:
            self.update_data_panel(self.base_info)
        self.kline_widget.update_data(df)
        fill_daily_table(self.kline_table, df)

    def on_error(self, msg):
        QMessageBox.critical(self, "错误", f"获取数据失败: {msg}")

    def update_data_panel(self, base):
        """更新上方数据面板内容"""
        self.name_label.setText(base.get('name', '--'))
        self.labels['date'].setText(base.get('date', '--'))

        def fmt(key, div=1000):
            val = base.get(key, 0)
            return f"{val / div:.2f}" if isinstance(val, (int, float)) else "--"

        self.labels['open'].setText(fmt('KaiPan'))
        self.labels['high'].setText(fmt('ZuiGao'))
        self.labels['low'].setText(fmt('ZuiDi'))
        self.labels['close'].setText(fmt('ZuoShou'))
        self.labels['振幅'].setText(f"{fmt('ZhenFu')}%")
        self.labels['内外比'].setText(fmt('NeiWaiBi'))
        self.labels['pe'].setText(fmt('ShiYingLv'))
        self.labels['pb'].setText(fmt('ShiJingLv'))
        self.labels['mkt_cap'].setText(f"{base.get('ShiZhi', 0):,.0f}")