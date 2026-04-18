# -*- coding: utf-8 -*-
"""
股票列表 Tab
"""
import time
import builtins
import pandas as pd
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QListWidget, QStyledItemDelegate, QStyle)
from PyQt6.QtGui import QFontMetrics, QColor, QBrush
from PyQt6.QtCore import Qt, pyqtSignal

from quant_system.services import DataPreprocessor
from quant_system.data.storage import bulk_upsert_from_df, load_stock_list_df


class NoFocusDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if option.state & QStyle.StateFlag.State_HasFocus:
            option.state = option.state & ~QStyle.StateFlag.State_HasFocus
        super().paint(painter, option, index)


class StockListTab(QWidget):
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

        self.category_list = QListWidget()
        self.category_list.setMaximumWidth(110)
        self.category_list.addItems(["全部", "沪市主板", "深市主板", "创业板", "科创板", "北交所"])
        self.category_list.setStyleSheet("""
            QListWidget { background-color: #1e1e1e; border: none; outline: 0; }
            QListWidget::item { color: #aaaaaa; padding: 15px 10px; border-radius: 5px; margin: 2px 5px; }
            QListWidget::item:hover { background-color: #2a2a2a; color: #ffffff; }
            QListWidget::item:selected { background-color: #2196F3; color: white; font-weight: bold; }
        """)
        self.category_list.itemClicked.connect(self.on_category_changed)
        layout.addWidget(self.category_list)

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
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1e1e1e; border: none; outline: 0; color: #d4d4d4; }
            QTableWidget::item { padding: 2px 5px; border-bottom: 1px solid #282828; }
            QTableWidget::item:hover { background-color: #2c2c2c; }
            QTableWidget::item:selected { background-color: #1a4b77; color: #ffffff; }
            QHeaderView::section { background-color: #252526; color: #888888; padding: 8px; border: none; border-bottom: 2px solid #333333; font-weight: bold; font-size: 13px; }
            QScrollBar:vertical { border: none; background: #1e1e1e; width: 10px; margin: 0px; }
            QScrollBar::handle:vertical { background: #555555; min-height: 30px; border-radius: 5px; }
            QScrollBar::handle:vertical:hover { background: #777777; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        fm = QFontMetrics(self.table.font())
        safe_base_w = fm.horizontalAdvance("0" * 12) + 20
        min_w = fm.horizontalAdvance("汉字") + 20
        self.table.horizontalHeader().setMinimumSectionSize(min_w)
        for i in range(7):
            self.table.setColumnWidth(i, safe_base_w)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        right_layout.addWidget(self.table)
        layout.addWidget(right_panel)

        self.cache_btn.clicked.connect(self.load_from_cache)
        self.update_btn.clicked.connect(self.force_update)

    def filter_table(self):
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

        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(df))

        def create_item(text):
            item = QTableWidgetItem(str(text))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            return item

        records = df.to_dict('records')
        for idx, row in enumerate(records):
            self.table.setItem(idx, 0, create_item(row.get('code', '--')))
            self.table.setItem(idx, 1, create_item(row.get('name', '--')))

            price = row.get('price', '--')
            pct = row.get('pct_chg', '--')
            pct_item = create_item(f"{pct}%" if pct != '--' else '--')
            try:
                if pct != '--':
                    pct_val = float(pct)
                    if pct_val > 0:
                        pct_item.setForeground(QColor("#ef5350"))
                        self.table.setItem(idx, 2, create_item(price))
                        self.table.item(idx, 2).setForeground(QColor("#ef5350"))
                    elif pct_val < 0:
                        pct_item.setForeground(QColor("#26a69a"))
                        self.table.setItem(idx, 2, create_item(price))
                        self.table.item(idx, 2).setForeground(QColor("#26a69a"))
            except:
                pass

            self.table.setItem(idx, 3, pct_item)
            self.table.setItem(idx, 4, create_item(row.get('high', '--')))
            self.table.setItem(idx, 5, create_item(row.get('low', '--')))
            self.table.setItem(idx, 6, create_item(row.get('volume', '--')))

        self.table.setSortingEnabled(True)
        self.table.setUpdatesEnabled(True)

    def on_category_changed(self, item):
        self.current_category = item.text()
        self.filter_table()

    def _load_sqlite_snapshot(self):
        try:
            db_df = load_stock_list_df()
            if db_df is not None and not db_df.empty:
                db_df['code'] = db_df['code'].astype(str).str.zfill(6)
                self.all_df = db_df[['code', 'name', 'price', 'pct_chg', 'high', 'low', 'volume']].copy()
                self.date_lbl.setText("行情日期: SQLite缓存")
                self.filter_table()
        except Exception as e:
            print(f"SQLite 启动加载失败: {e}")

    def _merge_db_prices(self, df):
        try:
            db_df = load_stock_list_df()
            if db_df is None or db_df.empty:
                return df
            merged = df.copy()
            merged['code'] = merged['code'].astype(str).str.zfill(6)
            db_mem = db_df[['code', 'price', 'pct_chg', 'high', 'low', 'volume']].copy()
            db_mem['code'] = db_mem['code'].astype(str).str.zfill(6)
            merged = merged.merge(db_mem, on='code', how='left', suffixes=('', '_db'))
            for col in ['price', 'pct_chg', 'high', 'low', 'volume']:
                merged[col] = merged[f'{col}_db'].where(merged[f'{col}_db'].notna(), merged[col])
                merged.drop(columns=[f'{col}_db'], inplace=True)
            return merged
        except Exception as e:
            print(f"SQLite 记忆合并失败: {e}")
            return df

    def load_from_cache(self):
        self.fetch_start_time = time.perf_counter()
        self._load_sqlite_snapshot()
        self._start_thread(True)

    def force_update(self):
        self.fetch_start_time = time.perf_counter()
        self._start_thread(False)

    def _start_thread(self, cache):
        from quant_system.stock.threads.stock_list_thread import StockListThread
        self.thread = StockListThread(use_cache=cache)
        self.thread.finished.connect(self.on_data_loaded)
        self.thread.start()

    def on_data_loaded(self, df, date):
        fetch_cost = time.perf_counter() - getattr(self, 'fetch_start_time', time.perf_counter())
        print(f"[性能计时] {time.perf_counter() - builtins.APP_START_TIME:.4f}s | 数据获取完成 (线程独立耗时: {fetch_cost:.4f}s)，准备渲染表格...")

        render_start = time.perf_counter()
        if df is not None and not df.empty:
            try:
                df['code'] = df['code'].astype(str).str.zfill(6)
            except Exception:
                pass
            self.all_df = self._merge_db_prices(df)
            bulk_upsert_from_df(self.all_df)
        else:
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
                import time as ti, builtins
                builtins.JUMP_START_TIME = ti.perf_counter()
                print(f"\n[性能计时] {ti.perf_counter() - builtins.APP_START_TIME:.4f}s | ---> 鼠标双击股票 {code}，触发详情页跳转...")
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

    def update_single_stock_price(self, code, data):
        print(f"[{time.strftime('%H:%M:%S')}] 收到广播 -> 股票: {code} | 现价: {data['price']} | 涨幅: {data['pct_chg']}%")

        if not hasattr(self, 'table'):
            return

        code = str(code).zfill(6)
        target_row = -1
        for row in range(self.table.rowCount()):
            item_code = self.table.item(row, 0)
            if item_code and item_code.text().zfill(6) == code:
                target_row = row
                break

        if target_row == -1:
            print(f"忽略: {code} 不在当前显示列表中")
        else:
            pct = float(data['pct_chg'])
            if pct > 0:
                color = QColor("#ef5350")
            elif pct < 0:
                color = QColor("#26a69a")
            else:
                color = QColor("#dddddd")

            update_map = {
                2: f"{data['price']:.2f}",
                3: f"{data['pct_chg']:.2f}%",
                4: f"{data['high']:.2f}",
                5: f"{data['low']:.2f}",
                6: f"{data['volume']:.0f}"
            }
            for col, text in update_map.items():
                item = self.table.item(target_row, col)
                if item:
                    item.setText(text)
                    if col in [2, 3]:
                        item.setForeground(QBrush(color))
                    else:
                        item.setForeground(QBrush(QColor("#d4d4d4")))
            self.table.viewport().update()

        if self.all_df is not None and not self.all_df.empty:
            self.all_df['code'] = self.all_df['code'].astype(str).str.zfill(6)
            idx = self.all_df.index[self.all_df['code'] == code]
            if len(idx) > 0:
                self.all_df.loc[idx, 'price'] = data['price']
                self.all_df.loc[idx, 'pct_chg'] = data['pct_chg']
                self.all_df.loc[idx, 'high'] = data['high']
                self.all_df.loc[idx, 'low'] = data['low']
                self.all_df.loc[idx, 'volume'] = data['volume']

        try:
            stock_name = None
            if self.all_df is not None and not self.all_df.empty:
                hit = self.all_df[self.all_df['code'].astype(str).str.zfill(6) == code]
                if not hit.empty and 'name' in hit.columns:
                    stock_name = hit.iloc[0].get('name')
            from quant_system.data.storage import upsert_stock_quote
            upsert_stock_quote(
                code=code,
                name=stock_name,
                price=data.get('price'),
                pct_chg=data.get('pct_chg'),
                high=data.get('high'),
                low=data.get('low'),
                volume=data.get('volume'),
            )
        except Exception as e:
            print(f"SQLite 写入失败: {e}")
