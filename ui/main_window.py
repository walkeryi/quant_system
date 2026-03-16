import sys
from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QStatusBar, QMessageBox,
                             QLineEdit, QLabel, QWidget, QHBoxLayout, QSizePolicy,
                             QTableWidget)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QModelIndex, QTimer
import pandas as pd

from ui.stock_list_tab import StockListTab
from ui.daily_tab import DailyTab
from ui.backtest_tab import BacktestTab
from ui.calendar_tab import CalendarTab
from ui.search_completer import SearchCompleter


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("量化交易系统")
        self.setGeometry(100, 100, 1300, 800)

        self.initUI()
        self.initMenu()
        self.initStatusBar()
        self.initGlobalSearch()

    def initUI(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.stock_list_tab = StockListTab()
        # 连接股票列表双击信号到个股详情加载方法
        self.stock_list_tab.stock_double_clicked.connect(self.load_stock_daily)

        self.daily_tab = DailyTab()
        self.backtest_tab = BacktestTab()
        self.calendar_tab = CalendarTab()

        self.tabs.addTab(self.stock_list_tab, "股票数据")
        self.tabs.addTab(self.daily_tab, "个股详情")
        self.tabs.addTab(self.backtest_tab, "策略回测")
        self.tabs.addTab(self.calendar_tab, "交易日历")

    def initGlobalSearch(self):
        """现代化全局搜索框"""
        self.search_completer = SearchCompleter(self)

        # 创建搜索框（将自动返回一个 QLineEdit）
        self.search_edit = self.search_completer.setup_search_box(self.menuBar())

        # 设置数据源
        self.search_completer.set_data_source(self._get_search_results)

        # 连接选中信号
        self.search_completer.item_selected.connect(self.on_search_item_selected)

        # --- 新增：将搜索框放入容器，设置右边距 ---
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 15, 0)  # 右边距15像素
        search_layout.addWidget(self.search_edit)

        # 放置在菜单栏右侧（使用容器）
        self.menuBar().setCornerWidget(search_container, Qt.Corner.TopRightCorner)

    def _get_search_results(self, keyword):
        """获取搜索结果 - 供搜索组件调用"""
        df = self.stock_list_tab.all_df
        if df is None or not keyword:
            return []

        # 模糊匹配代码和名称
        mask = (df['code'].astype(str).str.contains(keyword, case=False) |
                df['name'].str.contains(keyword, case=False))
        filtered = df[mask].head(10)

        # 格式化数据 [(code, name, exchange), ...]
        results = []
        for _, row in filtered.iterrows():
            code = str(row['code'])
            name = str(row['name'])
            exchange = self.stock_list_tab._get_exchange(code)
            results.append((code, name, exchange))

        return results

    def on_search_item_selected(self, code):
        """处理搜索项选择"""
        self.load_stock_daily(code)

    def load_stock_daily(self, code):
        """加载个股详情"""
        print(f"跳转到个股详情，代码: {code}")  # 调试输出
        self.tabs.setCurrentIndex(1)  # 切换到"个股详情"标签
        self.daily_tab.load_stock(code)

    def initMenu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        exit_act = QAction("退出", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

    def initStatusBar(self):
        self.statusBar().showMessage("系统就绪")