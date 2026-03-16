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
    stock_double_clicked = pyqtSignal(str)  # 定义信号，传递股票代码

    def __init__(self):
        super().__init__()
        self.dp = DataPreprocessor()
        self.all_df = None
        self.current_category = "全部"
        self.initUI()
        self.load_from_cache()
        # 连接表格的双击信号
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

        # 按钮栏
        tool_bar = QHBoxLayout()
        self.cache_btn = QPushButton("刷新缓存")
        self.update_btn = QPushButton("同步行情")
        self.date_lbl = QLabel("行情日期: --")
        tool_bar.addWidget(self.cache_btn)
        tool_bar.addWidget(self.update_btn)
        tool_bar.addStretch()
        tool_bar.addWidget(self.date_lbl)
        right_layout.addLayout(tool_bar)

        # 表格配置
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["代码", "名称", "最新价", "涨幅%", "最高", "最低", "成交量(手)"])

        # 核心设置：消除光标与虚线
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setItemDelegate(NoFocusDelegate())
        self.table.setStyleSheet("QTableWidget { outline: none; border: none; }")

        # 列宽美化
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
        """筛选逻辑：带安全性检查"""
        if self.all_df is None or self.all_df.empty:
            return
        df = self.all_df.copy()

        # 解决 KeyError: 'code' 问题：确保 code 是列而不是索引
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

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(df))

        def create_item(text):
            item = QTableWidgetItem(str(text))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            return item

        for idx, (_, row) in enumerate(df.iterrows()):
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

    def on_category_changed(self, item):
        self.current_category = item.text()
        self.filter_table()

    def load_from_cache(self):
        self._start_thread(True)

    def force_update(self):
        self._start_thread(False)

    def _start_thread(self, cache):
        self.thread = StockListThread(use_cache=cache)
        self.thread.finished.connect(self.on_data_loaded)
        self.thread.start()

    def on_data_loaded(self, df, date):
        self.all_df = df
        self.date_lbl.setText(f"行情日期: {date or '--'}")
        self.filter_table()

    def on_cell_double_clicked(self, row, column):
        """处理表格双击事件，获取股票代码并发射信号"""
        code_item = self.table.item(row, 0)  # 代码在第0列
        if code_item:
            code = code_item.text().strip()
            if code:
                print(f"双击股票，代码: {code}")  # 调试输出
                self.stock_double_clicked.emit(code)
            else:
                print("双击行但代码为空")
        else:
            print("双击行但获取代码项失败")

    def _get_exchange(self, code):
        """根据股票代码判断所属市场（供搜索框调用）"""
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