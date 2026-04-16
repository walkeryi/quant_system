# 文件路径: quant_system/ui/quant_backtest_tab.py
import os
import json
import pandas as pd
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
                             QPushButton, QLineEdit, QGroupBox, QHeaderView,
                             QFormLayout, QMessageBox, QSplitter, QTabWidget, QTableWidgetItem,
                             QPlainTextEdit, QDateEdit, QScrollArea, QFrame, QInputDialog,
                             QListWidget)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from ui.charts.backtest_chart import BacktestChart
from ui.threads.backtest_thread import BacktestThread
from ui.threads.optimizer_thread import OptimizerThread

# 预设的系统策略库
STRATEGY_CENTER_DATA = {
    "双均线金叉策略": {
        "desc": "经典趋势跟踪策略 (5日均线上穿20日均线买入)",
        "code": '''def generate_signals(df):
    # 策略逻辑：计算快慢均线并生成买卖信号
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()

    df['signal'] = 0
    df.loc[df['MA5'] > df['MA20'], 'signal'] = 1  
    df.loc[df['MA5'] <= df['MA20'], 'signal'] = -1 
    return df
'''
    },
    "RSI 均值回归": {
        "desc": "超跌反弹策略 (RSI<30买入，RSI>70卖出)",
        "code": '''def generate_signals(df):
    # 策略逻辑：利用 RSI 指标识别超买超卖区域
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df['signal'] = 0
    df.loc[df['RSI'] < 30, 'signal'] = 1
    df.loc[df['RSI'] > 70, 'signal'] = -1
    return df
'''
    }
}


class StrategyRow(QFrame):
    """'我的策略' 列表中的自定义交互行组件"""

    def __init__(self, name, parent_tab):
        super().__init__()
        self.setObjectName("StrategyRow")
        self.setStyleSheet(
            "#StrategyRow { border-bottom: 1px solid #333; padding: 5px; } #StrategyRow:hover { background-color: #2c2c2c; }")
        layout = QHBoxLayout(self)

        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #e8eaed;")
        layout.addWidget(self.name_label)
        layout.addStretch()

        btn_style = "QPushButton { padding: 4px 8px; font-size: 12px; border-radius: 3px; background-color: #333; color: white; }"
        self.btn_sim = QPushButton("▶ 回测")
        self.btn_set = QPushButton("⚙️ 编辑源码")
        self.btn_del = QPushButton("🗑️ 删除")

        self.btn_sim.setStyleSheet(btn_style + "QPushButton { color: #00e676; font-weight: bold; }")
        self.btn_set.setStyleSheet(btn_style)
        self.btn_del.setStyleSheet(btn_style)

        self.btn_sim.clicked.connect(lambda checked, n=name: parent_tab.run_my_strategy(n))
        self.btn_set.clicked.connect(lambda checked, n=name: parent_tab.edit_my_strategy(n))
        self.btn_del.clicked.connect(lambda checked, n=name: parent_tab.delete_my_strategy(n))

        layout.addWidget(self.btn_sim)
        layout.addWidget(self.btn_set)
        layout.addWidget(self.btn_del)


class QuantBacktestTab(QWidget):
    def __init__(self):
        super().__init__()
        self.my_strategies_file = "quant_system/cache/my_strategies.json"
        self.current_editing_strategy = None
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { padding: 10px 20px; font-size: 14px; font-weight: bold; }")

        self.center_tab = QWidget()
        self.my_strategy_tab = QWidget()

        self.initCenterTab()
        self.initMyStrategyTab()

        self.tabs.addTab(self.center_tab, "策略中心")
        self.tabs.addTab(self.my_strategy_tab, "我的策略")
        main_layout.addWidget(self.tabs)

    def initCenterTab(self):
        layout = QHBoxLayout(self.center_tab)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setStyleSheet(
            "QSplitter::handle { background-color: transparent; width: 4px; } QSplitter::handle:hover { background-color: #555555; }")

        # 1. 左侧策略选择列表
        self.center_list = QListWidget()
        self.center_list.setMinimumWidth(180)
        self.center_list.addItems(list(STRATEGY_CENTER_DATA.keys()))
        self.center_list.setStyleSheet("""
            QListWidget { background-color: #1e1e1e; border: 1px solid #333; outline: 0; padding: 6px; font-size: 14px; }
            QListWidget::item { color: #d4d4d4; padding: 12px 10px; margin-bottom: 3px; border-radius: 5px; }
            QListWidget::item:selected { background-color: #2196F3; color: white; font-weight: bold; }
        """)
        self.center_list.itemSelectionChanged.connect(self.on_strategy_selected)
        main_splitter.addWidget(self.center_list)

        # 2. 右侧大区：参数配置与图表展示
        right_container = QWidget()
        right_panel = QVBoxLayout(right_container)

        # 顶部参数栏
        param_bar = QHBoxLayout()
        self.input_code = QLineEdit("000001")
        self.input_code.setFixedWidth(80)
        self.date_start = QDateEdit(QDate.currentDate().addYears(-1))
        self.date_end = QDateEdit(QDate.currentDate())

        param_bar.addWidget(QLabel("代码:"))
        param_bar.addWidget(self.input_code)
        param_bar.addWidget(QLabel(" 起始:"))
        param_bar.addWidget(self.date_start)
        param_bar.addWidget(QLabel(" 结束:"))
        param_bar.addWidget(self.date_end)
        param_bar.addStretch()

        # 按钮组
        self.btn_run = QPushButton("▶ 执行单次测算")
        self.btn_run.setStyleSheet(
            "background-color: #e53935; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")
        self.btn_run.clicked.connect(self.run_center_backtest)

        self.btn_optimize = QPushButton("⚙️ 并行参数寻优")
        self.btn_optimize.setStyleSheet(
            "background-color: #673AB7; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")
        self.btn_optimize.clicked.connect(self.run_parameter_optimization)

        param_bar.addWidget(self.btn_run)
        param_bar.addWidget(self.btn_optimize)
        right_panel.addLayout(param_bar)

        # 中间：三图展示区 + 参数表格
        self.right_tabs = QTabWidget()
        self.right_tabs.setStyleSheet("QTabBar::tab { padding: 8px 25px; font-size: 13px; }")

        # Tab 1: 图表展示
        chart_container = QSplitter(Qt.Orientation.Horizontal)
        self.chart = BacktestChart()
        chart_container.addWidget(self.chart.canvas)

        self.param_table = QTableWidget(4, 2)
        self.param_table.setHorizontalHeaderLabels(["参数名", "当前值"])
        self.param_table.setFixedWidth(200)
        param_items = [("初始资金", "100000"), ("交易费率", "0.0003"), ("滑点", "0.01"), ("止损(%)", "5.0")]
        for i, (k, v) in enumerate(param_items):
            self.param_table.setItem(i, 0, QTableWidgetItem(k))
            self.param_table.setItem(i, 1, QTableWidgetItem(v))
        chart_container.addWidget(self.param_table)
        chart_container.setSizes([800, 200])

        self.right_tabs.addTab(chart_container, "📈 回测净值曲线")

        # Tab 2: 源码编辑器 (新版带日志控制台)
        source_container = QSplitter(Qt.Orientation.Vertical)
        source_container.setStyleSheet("QSplitter::handle { background-color: #333; height: 2px; }")

        # 2.1 上半部分：代码编辑器
        editor_group = QGroupBox("策略逻辑 (Python 代码)")
        editor_layout = QVBoxLayout(editor_group)
        self.lbl_desc = QLabel("策略描述加载中...")
        self.lbl_desc.setStyleSheet("color: #aaaaaa; font-style: italic;")
        self.source_viewer = QPlainTextEdit()
        self.source_viewer.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas; font-size: 13px;")

        self.btn_save_code = QPushButton("💾 保存修改")
        self.btn_save_code.setStyleSheet(
            "background-color: #4CAF50; color: white; border-radius: 3px; padding: 4px 10px;")
        self.btn_save_code.setVisible(False)
        self.btn_save_code.clicked.connect(self.save_current_code)

        editor_layout.addWidget(self.lbl_desc)
        editor_layout.addWidget(self.source_viewer)
        editor_layout.addWidget(self.btn_save_code, alignment=Qt.AlignmentFlag.AlignRight)

        source_container.addWidget(editor_group)

        # 2.2 下半部分：输出控制台
        self.console_tabs = QTabWidget()
        self.console_tabs.setStyleSheet("QTabBar::tab { padding: 4px 15px; font-size: 12px; }")

        # 运行日志框 (模仿 VSCode Terminal 风格)
        self.console_log = QPlainTextEdit()
        self.console_log.setReadOnly(True)
        self.console_log.setStyleSheet(
            "background-color: #0d1117; color: #58a6ff; font-family: Consolas; font-size: 13px;")

        # 错误清单框
        self.console_error = QPlainTextEdit()
        self.console_error.setReadOnly(True)
        self.console_error.setStyleSheet(
            "background-color: #0d1117; color: #ff7b72; font-family: Consolas; font-size: 13px;")

        self.console_tabs.addTab(self.console_log, "📝 运行日志 (Print输出)")
        self.console_tabs.addTab(self.console_error, "❌ 错误清单 (报错追踪)")

        source_container.addWidget(self.console_tabs)
        source_container.setSizes([600, 250])  # 设置上下比例 (代码为主，控制台为辅)

        self.right_tabs.addTab(source_container, "💻 源码编辑器")

        right_panel.addWidget(self.right_tabs)
        main_splitter.addWidget(right_container)
        main_splitter.setSizes([220, 1000])
        layout.addWidget(main_splitter)

        self.center_list.setCurrentRow(0)

    def initMyStrategyTab(self):
        layout = QVBoxLayout(self.my_strategy_tab)
        toolbar = QHBoxLayout()
        self.btn_new = QPushButton("+ 新建策略")
        self.btn_new.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 15px;")
        self.btn_new.clicked.connect(self.create_new_strategy)
        toolbar.addWidget(self.btn_new)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #1e1e1e; }")
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.list_container)
        layout.addWidget(scroll)
        self.refresh_my_strategies_list()

    # ================= 控制台辅助方法 =================
    def append_log(self, text):
        self.console_log.moveCursor(self.console_log.textCursor().MoveOperation.End)
        self.console_log.insertPlainText(text)
        self.console_log.verticalScrollBar().setValue(self.console_log.verticalScrollBar().maximum())

    def append_error(self, text):
        self.console_error.moveCursor(self.console_error.textCursor().MoveOperation.End)
        self.console_error.insertPlainText(text)
        self.console_error.verticalScrollBar().setValue(self.console_error.verticalScrollBar().maximum())

        # 自动跳转到错误面板
        self.right_tabs.setCurrentIndex(1)
        self.console_tabs.setCurrentIndex(1)

        # ================= 核心计算调度逻辑 =================

    def run_center_backtest(self):
        """执行基于纯 Python 内核的单次回测"""
        code = self.input_code.text().strip()
        strategy_code = self.source_viewer.toPlainText()
        start_date = self.date_start.date().toString("yyyy-MM-dd")
        end_date = self.date_end.date().toString("yyyy-MM-dd")

        try:
            capital = float(self.param_table.item(0, 1).text())
            stop_loss = float(self.param_table.item(3, 1).text())
        except:
            QMessageBox.warning(self, "错误", "回测参数格式不正确")
            return

        self.btn_run.setEnabled(False)
        self.btn_run.setText("⏳ 核心运算中...")

        # 每次运行前清空控制台
        self.console_log.clear()
        self.console_error.clear()
        self.console_tabs.setCurrentIndex(0)
        self.append_log(">>> 启动量化回测引擎...\n")

        self.thread = BacktestThread(code, strategy_code, start_date, end_date, capital, stop_loss)

        # 绑定日志和报错信号流
        self.thread.log_msg.connect(self.append_log)
        self.thread.error_msg.connect(self.append_error)

        self.thread.finished.connect(self.on_backtest_finished)
        self.thread.error.connect(self.on_backtest_error)
        self.thread.start()

    def on_backtest_finished(self, df, equity_df, trades, metrics):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("▶ 执行单次测算")
        self.chart.draw(df, equity_df, trades)

        # 成功后自动切回图表页面展示结果
        self.right_tabs.setCurrentIndex(0)

        QMessageBox.information(self, "测算完成",
                                f"总收益率: {metrics['total_return']:+.2f}%\n"
                                f"最大回撤: {metrics['max_drawdown']:.2f}%\n"
                                f"交易次数: {metrics['trade_count']}")

    def run_parameter_optimization(self):
        param_ranges = {
            'fast': range(5, 16, 2),
            'slow': range(20, 61, 5)
        }

        self.btn_optimize.setEnabled(False)
        self.opt_thread = OptimizerThread(
            self.input_code.text().strip(),
            self.source_viewer.toPlainText(),  # 新增：传入代码编辑器中的策略源码
            self.date_start.date().toString("yyyy-MM-dd"),
            self.date_end.date().toString("yyyy-MM-dd"),
            float(self.param_table.item(0, 1).text()),
            param_ranges
        )
        self.opt_thread.progress.connect(lambda p: self.btn_optimize.setText(f"寻优中 {p}%"))
        self.opt_thread.finished.connect(self.on_optimization_finished)
        self.opt_thread.start()

    def on_optimization_finished(self, result_df):
        self.btn_optimize.setEnabled(True)
        self.btn_optimize.setText("⚙️ 并行参数寻优")

        best = result_df.sort_values('return', ascending=False).iloc[0]
        msg = f"并行测算完成！共验证 {len(result_df)} 组组合。\n\n"
        msg += f"最佳参数: 快线({int(best['fast'])}), 慢线({int(best['slow'])})\n"
        msg += f"最高收益率: {best['return']:.2f}%"
        QMessageBox.information(self, "优化结果", msg)

    # ================= 辅助管理方法 =================
    def on_strategy_selected(self):
        item = self.center_list.currentItem()
        if not item: return
        data = STRATEGY_CENTER_DATA.get(item.text(), {})
        self.current_editing_strategy = None
        self.lbl_desc.setText(f"🔒 系统只读策略：{data.get('desc')}")
        self.source_viewer.setPlainText(data.get('code'))
        self.source_viewer.setReadOnly(True)
        self.btn_save_code.setVisible(False)

    def edit_my_strategy(self, name):
        data = self.load_my_strategies()
        if name in data:
            self.current_editing_strategy = name
            self.lbl_desc.setText(f"🟢 正在编辑：【{name}】 (修改后请保存)")
            self.source_viewer.setPlainText(data[name].get('code'))
            self.source_viewer.setReadOnly(False)
            self.btn_save_code.setVisible(True)
            self.tabs.setCurrentIndex(0)
            self.right_tabs.setCurrentIndex(1)

    def save_current_code(self):
        if not self.current_editing_strategy: return
        data = self.load_my_strategies()
        data[self.current_editing_strategy]['code'] = self.source_viewer.toPlainText()
        self.save_my_strategies(data)
        QMessageBox.information(self, "成功", "源码已保存")

    def load_my_strategies(self):
        if os.path.exists(self.my_strategies_file):
            with open(self.my_strategies_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_my_strategies(self, data):
        with open(self.my_strategies_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def refresh_my_strategies_list(self):
        for i in reversed(range(self.list_layout.count())):
            self.list_layout.itemAt(i).widget().setParent(None)
        data = self.load_my_strategies()
        for name in data:
            self.list_layout.addWidget(StrategyRow(name, self))

    def create_new_strategy(self):
        name, ok = QInputDialog.getText(self, "新建", "名称:")
        if ok and name.strip():
            data = self.load_my_strategies()
            data[name.strip()] = {"desc": "自定义策略",
                                  "code": "def generate_signals(df):\n    df['signal'] = 0\n    return df\n"}
            self.save_my_strategies(data)
            self.refresh_my_strategies_list()

    def delete_my_strategy(self, name):
        data = self.load_my_strategies()
        if name in data:
            del data[name]
            self.save_my_strategies(data)
            self.refresh_my_strategies_list()

    def run_my_strategy(self, name):
        self.edit_my_strategy(name)
        self.run_center_backtest()

    def on_backtest_error(self, msg):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("▶ 执行单次测算")
        QMessageBox.critical(self, "错误", msg)