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

        print(
            f"[性能计时] {time.perf_counter() - builtins.APP_START_TIME:.4f}s | 股票列表 UI 框架初始化完毕，开始请求/读取数据...")
        self.load_from_cache()
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)

    def initUI(self):
        layout = QHBoxLayout(self)

        # 左侧分类
        self.category_list = QListWidget()
        self.category_list.setMaximumWidth(110)
        self.category_list.addItems(["全部", "沪市主板", "深市主板", "创业板", "科创板", "北交所"])
        self.category_list.setCurrentRow(0)
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
        self.table.setFrameShape(QTableWidget.Shape.NoFrame)

        fm = QFontMetrics(self.table.font())
        base_w = fm.horizontalAdvance("0" * 9) + 10
        for i in range(7):
            self.table.setColumnWidth(i, base_w)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

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

        # ============ 核心加速区 ============
        # 1. 锁死表格的界面刷新，禁止一边插入一边重绘界面
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(df))

        def create_item(text):
            item = QTableWidgetItem(str(text))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            return item

        # 2. 将 DataFrame 转为字典列表（比 iterrows 遍历快数十倍）
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
        # 3. 数据全部塞进去后，再瞬间一次性重绘界面
        self.table.setUpdatesEnabled(True)
        # ==================================

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
        # 记录数据读取耗时
        fetch_cost = time.perf_counter() - getattr(self, 'fetch_start_time', time.perf_counter())
        print(
            f"[性能计时] {time.perf_counter() - builtins.APP_START_TIME:.4f}s | 数据获取完成 (线程独立耗时: {fetch_cost:.4f}s)，准备渲染表格...")

        # 记录表格绘制耗时
        render_start = time.perf_counter()
        self.all_df = df
        self.date_lbl.setText(f"行情日期: {date or '--'}")
        self.filter_table()
        render_cost = time.perf_counter() - render_start
        print(
            f"[性能计时] {time.perf_counter() - builtins.APP_START_TIME:.4f}s | UI 表格数据装载完毕 (渲染独立耗时: {render_cost:.4f}s)")

        # 打印总耗时总结
        total_time = time.perf_counter() - builtins.APP_START_TIME
        print(f"\n=======================================================")
        print(f"🚀 [性能计时] 数据完全加载完成！应用启动总耗时: {total_time:.4f} 秒")
        print(f"=======================================================\n")

    def on_cell_double_clicked(self, row, column):
        code_item = self.table.item(row, 0)
        if code_item:
            code = code_item.text().strip()
            if code:
                import time, builtins
                # 记录双击这一瞬间的时间点
                builtins.JUMP_START_TIME = time.perf_counter()
                print(
                    f"\n[性能计时] {time.perf_counter() - builtins.APP_START_TIME:.4f}s | ---> 鼠标双击股票 {code}，触发详情页跳转...")

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