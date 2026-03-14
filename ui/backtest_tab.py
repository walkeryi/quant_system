import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QDateEdit, QComboBox, QPushButton,
                             QTextEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox)
from PyQt6.QtCore import QDate, Qt, QThread, pyqtSignal
from data_preprocessing import DataPreprocessor


class BacktestThread(QThread):
    """回测线程（模拟）"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            # 获取日线数据（用于后续真实回测，目前仅用于模拟）
            dp = DataPreprocessor()
            df = dp.get_daily_data(
                self.params['symbol'],
                self.params['start_date'],
                self.params['end_date']
            )
            if df is None or df.empty:
                self.error.emit("无法获取日线数据，回测终止")
                return

            # 模拟回测计算
            import time
            time.sleep(2)  # 模拟耗时

            # 构造模拟结果
            days = len(df)
            final_value = self.params['cash'] * (1 + np.random.uniform(-0.1, 0.2))
            total_return = (final_value - self.params['cash']) / self.params['cash'] * 100
            sharpe = np.random.uniform(0.5, 2.5)
            max_drawdown = np.random.uniform(5, 20)

            text = (
                f"回测完成！\n"
                f"股票: {self.params['symbol']}\n"
                f"数据量: {days} 条交易日数据\n"
                f"初始资金: {self.params['cash']:.2f}\n"
                f"最终资金: {final_value:.2f}\n"
                f"总收益率: {total_return:.2f}%\n"
                f"夏普比率: {sharpe:.2f}\n"
                f"最大回撤: {max_drawdown:.2f}%\n"
            )

            # 生成模拟图表
            fig = Figure(figsize=(8, 5))
            ax = fig.add_subplot(111)
            ax.plot(np.cumprod(1 + np.random.randn(days) * 0.01), label='模拟净值')
            ax.set_title("模拟净值曲线")
            ax.legend()
            fig.tight_layout()

            # 模拟交易记录
            trades = pd.DataFrame({
                '日期': [df.index[0].strftime('%Y-%m-%d'), df.index[-1].strftime('%Y-%m-%d')],
                '操作': ['买入', '卖出'],
                '价格': [df.iloc[0]['close'], df.iloc[-1]['close']],
                '数量': [100, 100]
            })

            result = {
                'text': text,
                'figure': fig,
                'trades': trades
            }
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))


class BacktestTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)

        # 参数输入区域
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("股票代码:"))
        self.symbol_edit = QLineEdit("000001")
        param_layout.addWidget(self.symbol_edit)

        param_layout.addWidget(QLabel("开始日期:"))
        self.start_edit = QDateEdit(QDate.currentDate().addDays(-365))
        self.start_edit.setCalendarPopup(True)
        param_layout.addWidget(self.start_edit)

        param_layout.addWidget(QLabel("结束日期:"))
        self.end_edit = QDateEdit(QDate.currentDate())
        self.end_edit.setCalendarPopup(True)
        param_layout.addWidget(self.end_edit)

        param_layout.addWidget(QLabel("初始资金:"))
        self.cash_edit = QLineEdit("100000")
        param_layout.addWidget(self.cash_edit)

        param_layout.addWidget(QLabel("策略:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["双均线", "布林带", "RSI"])
        param_layout.addWidget(self.strategy_combo)

        self.run_btn = QPushButton("运行回测")
        self.run_btn.clicked.connect(self.run_backtest)
        param_layout.addWidget(self.run_btn)
        param_layout.addStretch()
        main_layout.addLayout(param_layout)

        # 结果显示区域（水平布局）
        result_layout = QHBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setMaximumWidth(350)
        self.result_text.setReadOnly(True)
        self.figure = Figure(figsize=(8, 5))
        self.canvas = FigureCanvas(self.figure)
        result_layout.addWidget(self.result_text)
        result_layout.addWidget(self.canvas)
        main_layout.addLayout(result_layout)

        # 交易记录表格
        self.trade_table = QTableWidget()
        self.trade_table.setColumnCount(4)
        self.trade_table.setHorizontalHeaderLabels(["日期", "操作", "价格", "数量"])
        self.trade_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.trade_table)

    def run_backtest(self):
        symbol = self.symbol_edit.text().strip()
        if not symbol:
            QMessageBox.warning(self, "警告", "请输入股票代码")
            return

        params = {
            'symbol': symbol,
            'start_date': self.start_edit.date().toString("yyyy-MM-dd"),
            'end_date': self.end_edit.date().toString("yyyy-MM-dd"),
            'cash': float(self.cash_edit.text()),
            'strategy': self.strategy_combo.currentText()
        }

        self.run_btn.setEnabled(False)
        self.run_btn.setText("运行中...")
        self.result_text.clear()
        self.trade_table.setRowCount(0)

        self.thread = BacktestThread(params)
        self.thread.finished.connect(self.on_data_loaded)
        self.thread.error.connect(self.on_backtest_error)
        self.thread.start()

    def on_backtest_finished(self, result):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("运行回测")
        self.result_text.setText(result['text'])

        self.figure.clear()
        self.figure = result['figure']
        self.canvas.figure = self.figure
        self.canvas.draw()

        trades_df = result['trades']
        self.trade_table.setRowCount(len(trades_df))
        for i, row in trades_df.iterrows():
            self.trade_table.setItem(i, 0, QTableWidgetItem(row['日期']))
            self.trade_table.setItem(i, 1, QTableWidgetItem(row['操作']))
            self.trade_table.setItem(i, 2, QTableWidgetItem(f"{row['价格']:.2f}"))
            self.trade_table.setItem(i, 3, QTableWidgetItem(str(row['数量'])))

    def on_backtest_error(self, msg):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("运行回测")
        QMessageBox.critical(self, "错误", f"回测失败：{msg}")