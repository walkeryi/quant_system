import sys
from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QStatusBar, QMessageBox,
                             QLineEdit, QLabel, QWidget, QHBoxLayout, QSizePolicy,
                             QTableWidget)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QModelIndex, QTimer

from ui.stock_list_tab import StockListTab
from ui.search_completer import SearchCompleter


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("量化交易系统")
        self.setGeometry(100, 100, 1300, 800)

        # === 懒加载组件占位符 ===
        self.daily_tab = None
        self.backtest_tab = None
        self.calendar_tab = None

        self.initUI()
        self.initMenu()
        self.initStatusBar()
        self.initGlobalSearch()

    def initUI(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 首屏只加载“股票列表”，保证极速启动
        self.stock_list_tab = StockListTab()
        self.stock_list_tab.stock_double_clicked.connect(self.load_stock_daily)
        self.tabs.addTab(self.stock_list_tab, "股票数据")

        # 其它标签页只放置空的占位组件
        self.tabs.addTab(QWidget(), "个股详情")
        self.tabs.addTab(QWidget(), "策略回测")
        self.tabs.addTab(QWidget(), "交易日历")

        # 绑定点击切换事件，触发懒加载
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        """当用户第一次点击其它Tab时，才真正初始化其UI及图表"""
        if index == 1 and self.daily_tab is None:
            # 延迟导入，减少主程序启动时的库解析耗时
            from ui.daily_tab import DailyTab
            self.daily_tab = DailyTab()
            self.tabs.removeTab(1)
            self.tabs.insertTab(1, self.daily_tab, "个股详情")
            self.tabs.setCurrentIndex(1)
        elif index == 2 and self.backtest_tab is None:
            from ui.backtest_tab import BacktestTab
            self.backtest_tab = BacktestTab()
            self.tabs.removeTab(2)
            self.tabs.insertTab(2, self.backtest_tab, "策略回测")
            self.tabs.setCurrentIndex(2)
        elif index == 3 and self.calendar_tab is None:
            from ui.calendar_tab import CalendarTab
            self.calendar_tab = CalendarTab()
            self.tabs.removeTab(3)
            self.tabs.insertTab(3, self.calendar_tab, "交易日历")
            self.tabs.setCurrentIndex(3)

    def load_stock_daily(self, code):
        if self.daily_tab is None:
            self.on_tab_changed(1)  # 强制触发懒加载
        else:
            self.tabs.setCurrentIndex(1)
        self.daily_tab.load_stock(code)

    def initGlobalSearch(self):
        self.search_completer = SearchCompleter(self)
        self.search_edit = self.search_completer.setup_search_box(self.menuBar())
        self.search_completer.set_data_source(self._get_search_results)
        self.search_completer.item_selected.connect(self.on_search_item_selected)

        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 15, 0)
        search_layout.addWidget(self.search_edit)
        self.menuBar().setCornerWidget(search_container, Qt.Corner.TopRightCorner)

    def _get_search_results(self, keyword):
        df = self.stock_list_tab.all_df
        if df is None or not keyword: return []
        mask = (df['code'].astype(str).str.contains(keyword, case=False) |
                df['name'].str.contains(keyword, case=False))
        filtered = df[mask].head(10)
        results = []
        for _, row in filtered.iterrows():
            results.append((str(row['code']), str(row['name']), self.stock_list_tab._get_exchange(str(row['code']))))
        return results

    def on_search_item_selected(self, code):
        self.load_stock_daily(code)

    def initMenu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        exit_act = QAction("退出", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

    def initStatusBar(self):
        self.statusBar().showMessage("系统就绪")