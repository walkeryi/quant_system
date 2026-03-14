import matplotlib
import pandas as pd
import requests
import logging
import os

# 1. 基础配置：必须在导入后端之前设置
matplotlib.use('QtAgg')
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False

# 2. 健壮的导入方案：解决 backend_qtagg 找不到引用的问题
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    # 针对旧版本 Matplotlib 的回退方案
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# 解决 figure 找不到引用的问题
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

logger = logging.getLogger('quant_system')


class FenshiDataThread(QThread):
    """UI 层的异步工作线程：仅负责数据抓取任务"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, code):
        super().__init__()
        self.code = code
        self.token = "f75cc676f91464a63112979b855c4164"

    def run(self):
        try:
            url = "http://www.sanhulianghua.com:2008/v1/hsa_fenshi"
            params = {"token": self.token, "code": self.code, "all": 1}
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            if data.get('ret') == 200:
                self.finished.emit(data)
            else:
                self.error.emit(data.get('msg', '获取分时数据失败'))
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

        # 图表区域：使用 Figure 实例
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
        if not code: return
        self.query_btn.setEnabled(False)
        self.query_btn.setText("获取中...")
        self.thread = FenshiDataThread(code)
        self.thread.finished.connect(self.on_data_ready)
        self.thread.error.connect(self.on_error)
        self.thread.start()

    def on_data_ready(self, full_data):
        self.query_btn.setEnabled(True)
        self.query_btn.setText("查看分时行情")

        base = full_data.get('base', {})
        points = full_data.get('data', [])
        if not points:
            QMessageBox.warning(self, "提醒", "该股票暂无分时数据")
            return

        df = pd.DataFrame(points)
        df['price'] = df['JiaGe'] / 1000
        df['avg_price'] = df['JunJia'] / 1000
        df['pct_chg'] = df['ZhangFu'] / 1000

        self.draw_chart(df, base)
        self.fill_table(df)
        self.save_csv(df, base)

    def fill_table(self, df):
        self.table.setRowCount(len(df))
        # 倒序显示，最新在最前
        for i, row in enumerate(df[::-1].itertuples()):
            self.table.setItem(i, 0, QTableWidgetItem(row.ShiJian))
            self.table.setItem(i, 1, QTableWidgetItem(f"{row.price:.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{row.avg_price:.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.ZongLiang)))
            chg_item = QTableWidgetItem(f"{row.pct_chg:+.2f}%")
            if row.pct_chg > 0:
                chg_item.setForeground(Qt.GlobalColor.red)
            elif row.pct_chg < 0:
                chg_item.setForeground(Qt.GlobalColor.green)
            self.table.setItem(i, 4, chg_item)

    def draw_chart(self, df, base):
        self.figure.clear()
        ax1 = self.figure.add_subplot(2, 1, 1)
        ax1.plot(df['ShiJian'], df['price'], color='#1E90FF', label='现价')
        ax1.plot(df['ShiJian'], df['avg_price'], color='#FFA500', label='均价')

        # 绘制昨收参考线
        zuo_shou = base.get('ZuoShou', 0) / 1000
        if zuo_shou > 0:
            ax1.axhline(y=zuo_shou, color='gray', linestyle='--', linewidth=0.8)

        ax1.set_title(f"{base.get('name')} {base.get('date')} 分时图")
        ax1.legend(loc='upper left')
        ax1.grid(True, linestyle=':', alpha=0.5)

        ax2 = self.figure.add_subplot(2, 1, 2, sharex=ax1)
        ax2.bar(df['ShiJian'], df['ZongLiang'], color='teal', alpha=0.6)
        ax2.set_ylabel("成交量(手)")

        tick_space = max(1, len(df) // 8)
        ax1.set_xticks(df['ShiJian'][::tick_space])
        self.figure.tight_layout()
        self.canvas.draw()

    def save_csv(self, df, base):
        path = "data/fenshi"
        os.makedirs(path, exist_ok=True)
        file_path = f"{path}/{base.get('code')}_{base.get('date')}.csv"
        df.to_csv(file_path, index=False, encoding='utf-8-sig')

    def on_error(self, msg):
        self.query_btn.setEnabled(True)
        self.query_btn.setText("查看分时行情")
        QMessageBox.critical(self, "错误", f"获取失败: {msg}")