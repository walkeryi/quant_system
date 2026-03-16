# ui/daily_tab.py
import matplotlib
import pandas as pd
import logging
import os
from config import FENSHI_DATA_DIR

matplotlib.use('QtAgg')
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from matplotlib.figure import Figure
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from data_preprocessing import DataPreprocessor   # 导入数据预处理类

logger = logging.getLogger('quant_system')


class FenshiDataThread(QThread):
    """UI 层异步线程：通过 DataPreprocessor 获取分时数据"""
    finished = pyqtSignal(object)   # 传递 DataFrame
    error = pyqtSignal(str)

    def __init__(self, code):
        super().__init__()
        self.code = code

    def run(self):
        try:
            dp = DataPreprocessor()
            df = dp.get_fenshi_data(self.code)
            if df is None or df.empty:
                self.error.emit("无法获取分时数据")
                return
            self.finished.emit(df)
        except Exception as e:
            self.error.emit(str(e))


class DailyTab(QWidget):
    """个股详情面板：负责展示和绘图"""

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # 顶部工具栏
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("股票代码:"))
        self.code_edit = QLineEdit("601857")
        ctrl.addWidget(self.code_edit)
        self.query_btn = QPushButton("查看分时行情")
        self.query_btn.clicked.connect(self.query_data)
        ctrl.addWidget(self.query_btn)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        # 图表区域
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, stretch=3)

        # 数据表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["时间", "价格", "均价", "成交量(手)", "涨幅"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, stretch=2)

    def load_stock(self, code):
        """外部（如搜索框）调用接口"""
        self.code_edit.setText(code)
        self.query_data()

    def query_data(self):
        code = self.code_edit.text().strip()
        if not code:
            return

        self.query_btn.setEnabled(False)
        self.query_btn.setText("获取中...")
        self.thread = FenshiDataThread(code)
        self.thread.finished.connect(self.on_data_ready)
        self.thread.error.connect(self.on_error)
        self.thread.start()

    def on_data_ready(self, df):
        self.query_btn.setEnabled(True)
        self.query_btn.setText("查看分时行情")

        base = df.attrs.get('base', {})
        if df.empty:
            QMessageBox.warning(self, "提醒", "该股票暂无分时数据")
            return

        # 保存到数据库
        # dp = DataPreprocessor()
        # inserted = dp.save_fenshi_to_db(df)
        # if inserted > 0:
        #     logger.info(f"成功保存 {inserted} 条分时记录到数据库")
        #     # 可选：在状态栏或提示框中显示
        #     # self.parent().statusBar().showMessage(f"已保存 {inserted} 条记录到数据库")
        # else:
        #     logger.warning("分时数据未保存到数据库")

        self.draw_chart(df, base)
        self.fill_table(df)
        self.save_csv(df, base)

    def fill_table(self, df):
        self.table.setRowCount(len(df))
        # 倒序显示，最新在最前
        for i, row in enumerate(df[::-1].itertuples()):
            self.table.setItem(i, 0, QTableWidgetItem(row.time))
            self.table.setItem(i, 1, QTableWidgetItem(f"{row.price:.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{row.avg_price:.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.volume)))
            chg_item = QTableWidgetItem(f"{row.pct_chg:+.2f}%")
            if row.pct_chg > 0:
                chg_item.setForeground(Qt.GlobalColor.red)
            elif row.pct_chg < 0:
                chg_item.setForeground(Qt.GlobalColor.green)
            self.table.setItem(i, 4, chg_item)

    def draw_chart(self, df, base):
        self.figure.clear()
        ax1 = self.figure.add_subplot(2, 1, 1)
        ax1.plot(df['time'], df['price'], color='#1E90FF', label='现价')
        ax1.plot(df['time'], df['avg_price'], color='#FFA500', label='均价')

        zuo_shou = base.get('zuoshou', 0)
        if zuo_shou > 0:
            ax1.axhline(y=zuo_shou, color='gray', linestyle='--', linewidth=0.8)

        ax1.set_title(f"{base.get('name')} {base.get('date')} 分时图")
        ax1.legend(loc='upper left')
        ax1.grid(True, linestyle=':', alpha=0.5)

        ax2 = self.figure.add_subplot(2, 1, 2, sharex=ax1)
        ax2.bar(df['time'], df['volume'], color='teal', alpha=0.6)
        ax2.set_ylabel("成交量(手)")

        tick_space = max(1, len(df) // 8)
        ax1.set_xticks(df['time'][::tick_space])
        self.figure.tight_layout()
        self.canvas.draw()

    def save_csv(self, df, base):
        # 使用统一的缓存目录
        os.makedirs(FENSHI_DATA_DIR, exist_ok=True)
        file_path = os.path.join(FENSHI_DATA_DIR, f"{base.get('code')}_{base.get('date')}.csv")
        df.to_csv(file_path, index=False, encoding='utf-8-sig')

    def on_error(self, msg):
        self.query_btn.setEnabled(True)
        self.query_btn.setText("查看分时行情")
        QMessageBox.critical(self, "错误", f"获取失败: {msg}")

