# ui/daily_tab.py
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget)
from PyQt6.QtCore import Qt

from data_preprocessing import DataPreprocessor
from ui.widgets.stock_tab import StockTab

logger = logging.getLogger('quant_system')


class DailyTab(QWidget):
    """个股详情主面板：多标签页，每个股票一个标签页"""
    def __init__(self):
        super().__init__()
        self.stock_codes = []  # 缓存股票代码列表，用于切换
        self.initUI()
        self.load_stock_list()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        layout.addWidget(self.tab_widget)

    def load_stock_list(self):
        """从 DataPreprocessor 获取股票代码列表并缓存"""
        try:
            dp = DataPreprocessor()
            result = dp.get_stock_list(use_cache=True)
            if isinstance(result, tuple):
                df, _ = result
            else:
                df = result
            if df is not None and not df.empty:
                self.stock_codes = df['code'].astype(str).str.zfill(6).tolist()
        except Exception as e:
            logger.error(f"加载股票列表失败: {e}")

    def open_stock_tab(self, code):
        """打开或切换到指定股票的标签页"""
        # 检查是否已存在
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == code:
                self.tab_widget.setCurrentIndex(i)
                return

        # 创建新标签页
        stock_tab = StockTab(code)
        stock_tab.switch_requested.connect(self.on_switch_requested)
        self.tab_widget.addTab(stock_tab, code)
        self.tab_widget.setCurrentWidget(stock_tab)

        # 默认加载分时数据（第一个子标签页）
        stock_tab.load_fenshi_data()

    def on_switch_requested(self, delta):
        """处理切换股票请求"""
        current_index = self.tab_widget.currentIndex()
        if current_index == -1:
            return
        current_code = self.tab_widget.tabText(current_index)

        if not self.stock_codes:
            return

        try:
            current_pos = self.stock_codes.index(current_code)
        except ValueError:
            return

        new_pos = current_pos + delta
        if 0 <= new_pos < len(self.stock_codes):
            new_code = self.stock_codes[new_pos]
            self.open_stock_tab(new_code)

    def close_tab(self, index):
        widget = self.tab_widget.widget(index)
        if widget:
            widget.deleteLater()
        self.tab_widget.removeTab(index)

    def load_stock(self, code):
        """外部调用接口（如从股票列表双击）"""
        self.open_stock_tab(code)