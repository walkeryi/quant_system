# ui/stock_list_tab.py
import time
import builtins
import pandas as pd
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QListWidget, QStyledItemDelegate, QStyle)
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtCore import Qt, pyqtSignal
from .stock_list_thread import StockListThread
from data_preprocessing import DataPreprocessor

class NoFocusDelegate(QStyledItemDelegate):
    """强力消除单元格选中时的虚线框"""
    def paint(self, painter, option, index):
        if option.state & QStyle.StateFlag.State_HasFocus:
            option.state = option.state & ~QStyle.StateFlag.State_HasFocus
        super().paint(painter, option, index)

class StockListTab(QWidget):
    """股票列表页：支持双击跳转个股详情"""
    stock_double_clicked = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.dp = DataPreprocessor()
        self.all_df = None
        self.current_category = "全部"
        self.initUI()

        print(f"[性能计时] {time.perf_counter() - builtins.APP_START_TIME:.4f}s | 股票列表 UI 框架初始化完毕，开始请求/读取数据...")
        self.load_from_cache()
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)

    def initUI(self):
        layout = QHBoxLayout(self)

        # 左侧分类
        self.category_list = QListWidget()
        self.category_list.setMaximumWidth(110)
        self.category_list.addItems(["全部", "沪市主板", "深市主板", "创业板", "科创板", "北交所"])
        self.category_list.setStyleSheet("""
                    QListWidget {
                        background-color: #1e1e1e;
                        border: none;
                        outline: 0; /* 消除虚线框 */
                    }
                    QListWidget::item {
                        color: #aaaaaa;
                        padding: 15px 10px; /* 撑开高度 */
                        border-radius: 5px;
                        margin: 2px 5px;    /* 左右留白 */
                    }
                    QListWidget::item:hover {
                        background-color: #2a2a2a;
                        color: #ffffff;
                    }
                    QListWidget::item:selected {
                        background-color: #2196F3;
                        color: white;
                        font-weight: bold;
                    }
                """)
        # 👆 新增结束

        self.category_list.itemClicked.connect(self.on_category_changed)
        layout.addWidget(self.category_list)

        # 右侧内容
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        tool_bar = QHBoxLayout()
        self.cache_btn = QPushButton("刷新缓存")
        self.update_btn = QPushButton("同步行情")
        self.date_lbl = QLabel("行情日期: --")
        tool_bar.addWidget(self.cache_btn)
        tool_bar.addWidget(self.update_btn)
        tool_bar.addStretch()
        tool_bar.addWidget(self.date_lbl)
        right_layout.addLayout(tool_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["代码", "名称", "最新价", "涨幅%", "最高", "最低", "成交量(手)"])

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setItemDelegate(NoFocusDelegate())
        # 使用原生 C++ API 去除边框，消灭警告
        self.table.setFrameShape(QTableWidget.Shape.NoFrame)

        # 👇 新增：强制隐藏网格线和左侧自带的默认行号（序号）
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)

        # 👇 新增：右侧股票列表的现代化暗黑 UI 样式（包含定制滚动条）
        self.table.setStyleSheet("""
                    /* 表格全局背景 */
                    QTableWidget {
                        background-color: #1e1e1e;
                        border: none;
                        outline: 0;
                    }
                    /* 每一行的单元格 */
                    QTableWidget::item {
                        padding: 2px 5px;
                        border-bottom: 1px solid #282828; /* 用极淡的底边框替代全包围网格线 */
                        color: #d4d4d4;
                    }
                    /* 鼠标悬停时的整行高亮 */
                    QTableWidget::item:hover {
                        background-color: #2c2c2c;
                    }
                    /* 选中时的整行颜色 */
                    QTableWidget::item:selected {
                        background-color: #1a4b77; /* 沉稳的暗蓝色选中效果 */
                        color: #ffffff;
                    }
                    /* 现代化的表头设计 */
                    QHeaderView::section {
                        background-color: #252526;
                        color: #888888;
                        padding: 8px;
                        border: none;
                        border-bottom: 2px solid #333333;
                        font-weight: bold;
                        font-size: 13px;
                    }
                    /* 竖向滚动条 */
                    QScrollBar:vertical {
                        border: none; background: #1e1e1e; width: 10px; margin: 0px;
                    }
                    QScrollBar::handle:vertical {
                        background: #555555; min-height: 30px; border-radius: 5px;
                    }
                    QScrollBar::handle:vertical:hover { background: #777777; }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
                    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
                """)
        # 👆 新增结束

        fm = QFontMetrics(self.table.font())
        # ... 后续的 setColumnWidth 等代码保持不变 ...

        fm = QFontMetrics(self.table.font())
        # 假设最长的是成交量（例如 "12345678.00"），我们用 12 个 "0" 加上 20 像素的留白做标尺
        safe_base_w = fm.horizontalAdvance("0" * 12) + 20
        min_w = fm.horizontalAdvance("汉字") + 20
        self.table.horizontalHeader().setMinimumSectionSize(min_w)
        # 循环应用到所有列
        for i in range(7):
            self.table.setColumnWidth(i, safe_base_w)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        self.table.setSortingEnabled(True)
        right_layout.addWidget(self.table)
        layout.addWidget(right_panel)

        self.cache_btn.clicked.connect(self.load_from_cache)
        self.update_btn.clicked.connect(self.force_update)

    def filter_table(self):
        """极速筛选与渲染逻辑"""
        if self.all_df is None or self.all_df.empty:
            return
        df = self.all_df.copy()

        if 'code' not in df.columns:
            df = df.reset_index()

        if self.current_category != "全部":
            codes = df['code'].astype(str).str.zfill(6)
            if self.current_category == "沪市主板":
                m = codes.str.startswith('60')
            elif self.current_category == "深市主板":
                m = codes.str.startswith('00')
            elif self.current_category == "创业板":
                m = codes.str.startswith('30')
            elif self.current_category == "科创板":
                m = codes.str.startswith('688')
            elif self.current_category == "北交所":
                m = codes.str.startswith(('8', '9', '4'))
            df = df[m]

        # 1. 锁死表格的界面刷新
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(df))

        def create_item(text):
            item = QTableWidgetItem(str(text))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            return item

        # 2. 将 DataFrame 转为字典列表加速渲染
        records = df.to_dict('records')

        for idx, row in enumerate(records):
            self.table.setItem(idx, 0, create_item(row.get('code', '--')))
            self.table.setItem(idx, 1, create_item(row.get('name', '--')))

            price = row.get('price', '--')
            pct = row.get('pct_chg', '--')
            self.table.setItem(idx, 2, create_item(price))

            pct_item = create_item(f"{pct}%" if pct != '--' else '--')
            try:
                if pct != '--' and float(pct) > 0:
                    pct_item.setForeground(Qt.GlobalColor.red)
                elif pct != '--' and float(pct) < 0:
                    pct_item.setForeground(Qt.GlobalColor.green)
            except:
                pass

            self.table.setItem(idx, 3, pct_item)
            self.table.setItem(idx, 4, create_item(row.get('high', '--')))
            self.table.setItem(idx, 5, create_item(row.get('low', '--')))
            self.table.setItem(idx, 6, create_item(row.get('volume', '--')))

        self.table.setSortingEnabled(True)
        # 3. 瞬间一次性重绘界面
        self.table.setUpdatesEnabled(True)

    def on_category_changed(self, item):
        self.current_category = item.text()
        self.filter_table()

    def load_from_cache(self):
        self.fetch_start_time = time.perf_counter()
        self._start_thread(True)

    def force_update(self):
        self.fetch_start_time = time.perf_counter()
        self._start_thread(False)

    def _start_thread(self, cache):
        self.thread = StockListThread(use_cache=cache)
        self.thread.finished.connect(self.on_data_loaded)
        self.thread.start()

    def on_data_loaded(self, df, date):
        fetch_cost = time.perf_counter() - getattr(self, 'fetch_start_time', time.perf_counter())
        print(f"[性能计时] {time.perf_counter() - builtins.APP_START_TIME:.4f}s | 数据获取完成 (线程独立耗时: {fetch_cost:.4f}s)，准备渲染表格...")

        render_start = time.perf_counter()
        self.all_df = df
        self.date_lbl.setText(f"行情日期: {date or '--'}")
        self.filter_table()
        render_cost = time.perf_counter() - render_start
        print(f"[性能计时] {time.perf_counter() - builtins.APP_START_TIME:.4f}s | UI 表格数据装载完毕 (渲染独立耗时: {render_cost:.4f}s)")

        total_time = time.perf_counter() - builtins.APP_START_TIME
        print(f"\n=======================================================")
        print(f" [性能计时] 数据完全加载完成！应用启动总耗时: {total_time:.4f} 秒")
        print(f"=======================================================\n")

    def on_cell_double_clicked(self, row, column):
        code_item = self.table.item(row, 0)
        if code_item:
            code = code_item.text().strip()
            if code:
                import time, builtins
                builtins.JUMP_START_TIME = time.perf_counter()
                print(f"\n[性能计时] {time.perf_counter() - builtins.APP_START_TIME:.4f}s | ---> 鼠标双击股票 {code}，触发详情页跳转...")
                self.stock_double_clicked.emit(code)

    def _get_exchange(self, code):
        code = str(code).zfill(6)
        if code.startswith('60'):
            return '沪市'
        elif code.startswith('00'):
            return '深市'
        elif code.startswith('30'):
            return '创业板'
        elif code.startswith('688'):
            return '科创板'
        elif code.startswith(('8', '9', '4')):
            return '北交所'
        else:
            return '其他'