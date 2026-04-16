# -*- coding: utf-8 -*-

# 文件路径: quant_system/ui/quant_backtest_tab.py

import os

import json

import time

import hashlib

import traceback

import pandas as pd

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,

                             QPushButton, QLineEdit, QGroupBox, QHeaderView,

                             QFormLayout, QMessageBox, QSplitter, QTabWidget, QTableWidgetItem,

                             QPlainTextEdit, QDateEdit, QScrollArea, QFrame, QInputDialog,

                             QDialog, QGridLayout,

                             QListWidget, QFileDialog, QApplication)

from PyQt6.QtCore import Qt, QDate

from PyQt6.QtGui import QFont



from ui.charts.backtest_chart import BacktestChart

from ui.threads.backtest_thread import BacktestThread

from ui.threads.optimizer_thread import OptimizerThread

from login import Session



# 预设的系统策略库

STRATEGY_CENTER_DATA = {

    "单均线趋势策略": {

        "desc": "简单趋势跟踪 (价格站上20日均线买入，跌破卖出)",

        "code": '''def generate_signals(df):

    df['MA20'] = df['close'].rolling(window=20).mean()

    df['signal'] = 0

    df.loc[df['close'] > df['MA20'], 'signal'] = 1

    df.loc[df['close'] <= df['MA20'], 'signal'] = -1

    return df

'''

    },

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

    "MACD 经典策略": {

        "desc": "利用指数平滑异同平均线进行交叉买卖",

        "code": '''def generate_signals(df):

    exp1 = df['close'].ewm(span=12, adjust=False).mean()

    exp2 = df['close'].ewm(span=26, adjust=False).mean()

    df['macd'] = exp1 - exp2

    df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()

    df['signal'] = 0

    df.loc[df['macd'] > df['signal_line'], 'signal'] = 1

    df.loc[df['macd'] < df['signal_line'], 'signal'] = -1

    return df

'''

    },

    "布林带均值回归": {

        "desc": "跌破下轨买入，触碰上轨卖出",

        "code": '''def generate_signals(df):

    df['MA20'] = df['close'].rolling(20).mean()

    df['std'] = df['close'].rolling(20).std()

    df['upper'] = df['MA20'] + 2 * df['std']

    df['lower'] = df['MA20'] - 2 * df['std']

    df['signal'] = 0

    df.loc[df['close'] < df['lower'], 'signal'] = 1

    df.loc[df['close'] > df['upper'], 'signal'] = -1

    return df

'''

    },

    "海龟交易策略 (简化版)": {

        "desc": "经典唐奇安通道突破策略",

        "code": '''def generate_signals(df):

    df['high_20'] = df['high'].rolling(20).max().shift(1)

    df['low_10'] = df['low'].rolling(10).min().shift(1)

    df['signal'] = 0

    df.loc[df['close'] > df['high_20'], 'signal'] = 1

    df.loc[df['close'] < df['low_10'], 'signal'] = -1

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

    },

    "深度学习 LSTM 模型": {

        "desc": "预测下一日涨跌并生成信号 (需预训练模型，此处为结构演示)",

        "code": '''def generate_signals(df):

    # 模拟 LSTM 预测逻辑

    # 实际应用中会加载：model = load_model('lstm_v1.h5')

    df['pred'] = df['close'].pct_change().shift(-1).rolling(5).mean()

    df['signal'] = 0

    df.loc[df['pred'] > 0.005, 'signal'] = 1

    df.loc[df['pred'] < -0.005, 'signal'] = -1

    return df

'''

    }

}





class StrategyRow(QFrame):

    ""



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

        self.btn_share = QPushButton("🔗 分享")



        self.btn_sim.setStyleSheet(btn_style + "QPushButton { color: #00e676; font-weight: bold; }")

        self.btn_set.setStyleSheet(btn_style)

        self.btn_del.setStyleSheet(btn_style)

        self.btn_share.setStyleSheet(btn_style)



        self.btn_sim.clicked.connect(lambda checked, n=name: parent_tab.run_my_strategy(n))

        self.btn_set.clicked.connect(lambda checked, n=name: parent_tab.edit_my_strategy(n))

        self.btn_del.clicked.connect(lambda checked, n=name: parent_tab.delete_my_strategy(n))

        self.btn_share.clicked.connect(lambda checked, n=name: parent_tab.share_strategy(n))



        layout.addWidget(self.btn_sim)

        layout.addWidget(self.btn_set)

        layout.addWidget(self.btn_share)

        layout.addWidget(self.btn_del)





class ReportRow(QFrame):

    def __init__(self, report_data, parent_tab):

        super().__init__()

        self.report_id = report_data['id']

        self.setObjectName("ReportRow")

        self.setStyleSheet("#ReportRow { border-bottom: 1px solid #333; padding: 12px; } #ReportRow:hover { background-color: #2c2c2c; }")

        layout = QHBoxLayout(self)



        info_layout = QVBoxLayout()

        self.title_label = QLabel(report_data.get('title', '未命名报告'))

        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #00e676;")

        cond = report_data.get('conditions', {})

        metric = report_data.get('metrics', {})

        detail_label = QLabel(

            f"标的: {cond.get('code', '--')} | 收益率: {metric.get('total_return', 0):+.2f}% | 创建: {report_data.get('timestamp', '--')}"

        )

        detail_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")

        info_layout.addWidget(self.title_label)

        info_layout.addWidget(detail_label)

        layout.addLayout(info_layout)

        layout.addStretch()



        btn_style = "QPushButton { padding: 5px 10px; border-radius: 3px; background: #333; color: #ddd; }"

        self.btn_view = QPushButton("👁️ 查看")

        self.btn_edit = QPushButton("✏️ 修改标题")

        self.btn_share = QPushButton("🔗 分享")

        self.btn_del = QPushButton("🗑️ 删除")

        for btn in [self.btn_view, self.btn_edit, self.btn_share, self.btn_del]:

            btn.setStyleSheet(btn_style)

            layout.addWidget(btn)



        self.btn_view.clicked.connect(lambda: parent_tab.view_report_detail(self.report_id))

        self.btn_edit.clicked.connect(lambda: parent_tab.on_edit_report_title(self.report_id))

        self.btn_del.clicked.connect(lambda: parent_tab.on_delete_report(self.report_id))

        self.btn_share.clicked.connect(lambda: parent_tab.on_share_report(self.report_id))





class QuantBacktestTab(QWidget):

    def __init__(self):

        super().__init__()

        self.my_strategies_file = "quant_system/cache/my_strategies.json"

        self.reports_file = "quant_system/cache/backtest_reports.json"

        self.current_editing_strategy = None

        self.last_metrics = None

        self.last_run_data = None

        self.initUI()



    def initUI(self):

        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        self.tabs.setStyleSheet("QTabBar::tab { padding: 10px 20px; font-size: 14px; font-weight: bold; }")



        self.center_tab = QWidget()

        self.my_strategy_tab = QWidget()

        self.reports_tab = QWidget()



        self.initCenterTab()

        self.initMyStrategyTab()

        self.initReportsTab()



        self.tabs.addTab(self.center_tab, "策略中心")

        self.tabs.addTab(self.my_strategy_tab, "我的策略")

        self.tabs.addTab(self.reports_tab, "回测报告")

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

        self.center_list.setStyleSheet("")

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



        self.btn_export = QPushButton("📊 导出回测报告")

        self.btn_export.setStyleSheet(

            "background-color: #607D8B; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")

        self.btn_export.setEnabled(False)

        self.btn_export.clicked.connect(self.export_report)

        self.btn_save_report = QPushButton("💾 保存为报告")

        self.btn_save_report.setStyleSheet(

            "background-color: #009688; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")

        self.btn_save_report.setEnabled(False)

        self.btn_save_report.clicked.connect(self.save_current_as_report)



        param_bar.addWidget(self.btn_run)

        param_bar.addWidget(self.btn_optimize)

        param_bar.addWidget(self.btn_export)

        param_bar.addWidget(self.btn_save_report)

        right_panel.addLayout(param_bar)



        # 中间：三图展示区 + 源码编辑器大Tab

        self.right_tabs = QTabWidget()

        self.right_tabs.setStyleSheet("QTabBar::tab { padding: 8px 25px; font-size: 13px; }")



        # 【Tab 1】: 图表展示

        chart_container = QSplitter(Qt.Orientation.Horizontal)

        self.chart = BacktestChart()

        chart_container.addWidget(self.chart.canvas)



        self.param_table = QTableWidget(4, 2)

        self.param_table.setHorizontalHeaderLabels(["参数名", "当前值"])

        self.param_table.setFixedWidth(200)

        param_items = [("初始资金", "100000"), ("交易费率", "0.0003"), ("单笔数量", "100"), ("止损(%)", "5.0")]

        for i, (k, v) in enumerate(param_items):

            self.param_table.setItem(i, 0, QTableWidgetItem(k))

            self.param_table.setItem(i, 1, QTableWidgetItem(v))

        chart_container.addWidget(self.param_table)

        chart_container.setSizes([800, 200])



        self.right_tabs.addTab(chart_container, "📈 回测净值曲线")



        # 【Tab 2】: 源码编辑器 (新版带下部输出控制台)

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

        self.btn_save_as_new = QPushButton("📝 另存为自定义策略")

        self.btn_save_as_new.setStyleSheet(

            "background-color: #0288D1; color: white; border-radius: 3px; padding: 4px 10px;")

        self.btn_save_as_new.clicked.connect(self.save_as_custom_strategy)



        editor_layout.addWidget(self.lbl_desc)

        editor_layout.addWidget(self.source_viewer)

        editor_layout.addWidget(self.btn_save_as_new, alignment=Qt.AlignmentFlag.AlignRight)

        editor_layout.addWidget(self.btn_save_code, alignment=Qt.AlignmentFlag.AlignRight)



        source_container.addWidget(editor_group)



        # 2.2 下半部分：输出控制台

        self.console_tabs = QTabWidget()

        self.console_tabs.setStyleSheet("QTabBar::tab { padding: 4px 15px; font-size: 12px; }")



        self.console_log = QPlainTextEdit()

        self.console_log.setReadOnly(True)

        self.console_log.setStyleSheet(

            "background-color: #0d1117; color: #58a6ff; font-family: Consolas; font-size: 13px;")



        self.console_error = QPlainTextEdit()

        self.console_error.setReadOnly(True)

        self.console_error.setStyleSheet(

            "background-color: #0d1117; color: #ff7b72; font-family: Consolas; font-size: 13px;")



        self.console_tabs.addTab(self.console_log, "📝 运行日志 (Print输出)")

        self.console_tabs.addTab(self.console_error, "❌ 错误清单 (报错追踪)")



        source_container.addWidget(self.console_tabs)

        source_container.setSizes([600, 250])  # 设置代码框和控制台的高度比例



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



    def initReportsTab(self):

        layout = QVBoxLayout(self.reports_tab)

        tool = QHBoxLayout()

        tool.addWidget(QLabel("回测报告列表"))

        tool.addStretch()

        self.btn_refresh_reports = QPushButton("刷新")

        self.btn_refresh_reports.clicked.connect(self.refresh_reports_list)

        tool.addWidget(self.btn_refresh_reports)

        layout.addLayout(tool)



        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setStyleSheet("QScrollArea { border: none; background-color: #1e1e1e; }")

        self.report_container = QWidget()

        self.report_layout = QVBoxLayout(self.report_container)

        self.report_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.report_container)

        layout.addWidget(scroll)

        self.refresh_reports_list()



    # ================= UI 控制台辅助方法 =================



    def append_log(self, text):

        self.console_log.moveCursor(self.console_log.textCursor().MoveOperation.End)

        self.console_log.insertPlainText(text)

        self.console_log.verticalScrollBar().setValue(self.console_log.verticalScrollBar().maximum())



    def append_error(self, text):

        self.console_error.moveCursor(self.console_error.textCursor().MoveOperation.End)

        self.console_error.insertPlainText(text)

        self.console_error.verticalScrollBar().setValue(self.console_error.verticalScrollBar().maximum())

        # 发生错误时自动切到报错页签

        self.right_tabs.setCurrentIndex(1)

        self.console_tabs.setCurrentIndex(1)



        # ================= 核心计算调度逻辑 =================



    def run_center_backtest(self):

        ""

        code = self.input_code.text().strip()

        strategy_code = self.source_viewer.toPlainText()

        start_date = self.date_start.date().toString("yyyy-MM-dd")

        end_date = self.date_end.date().toString("yyyy-MM-dd")



        try:

            capital = float(self.param_table.item(0, 1).text())

            quantity = int(self.param_table.item(2, 1).text())

            stop_loss = float(self.param_table.item(3, 1).text())



            self.console_log.clear()

            self.console_error.clear()

            self.console_tabs.setCurrentIndex(0)

            self.append_log(f">>> 启动量化回测引擎 (单次测算标的: {code})...\n")



            self.btn_run.setEnabled(False)

            self.btn_run.setText("⏳ 核心运算中...")



            self.thread = BacktestThread(code, strategy_code, start_date, end_date, capital, stop_loss, quantity)



            # 绑定控制台信号流

            self.thread.log_msg.connect(self.append_log)

            self.thread.error_msg.connect(self.append_error)



            self.thread.finished.connect(self.on_backtest_finished)

            self.thread.error.connect(self.on_backtest_error)

            self.thread.start()



        except Exception as e:

            self.append_error(f"【主程序错误】单次测算启动失败:\n{traceback.format_exc()}")

            self.btn_run.setEnabled(True)

            self.btn_run.setText("▶ 执行单次测算")



    def on_backtest_finished(self, df, equity_df, trades, metrics):

        self.btn_run.setEnabled(True)

        self.btn_run.setText("▶ 执行单次测算")

        self.chart.draw(df, equity_df, trades)

        self.last_metrics = metrics

        self.btn_export.setEnabled(True)

        self.btn_save_report.setEnabled(True)

        self.last_run_data = {

            "code": self.input_code.text().strip(),

            "capital": float(self.param_table.item(0, 1).text()),

            "start": self.date_start.date().toString("yyyy-MM-dd"),

            "end": self.date_end.date().toString("yyyy-MM-dd"),

            "metrics": metrics,

            "strategy_code": self.source_viewer.toPlainText(),

            "strategy_name": self.center_list.currentItem().text() if self.center_list.currentItem() else "自定义策略",

            "trades": trades

        }



        # 测算成功后，自动切回第一页展示图表

        self.right_tabs.setCurrentIndex(0)



        msg = (f"📈 测算完成！客观指标如下：\n\n"

               f"💰 总收益: {metrics['total_profit']:.2f} 元\n"

               f"📊 策略收益: {metrics['total_return']:+.2f}% | 标的自然涨幅: {metrics['buy_hold_return']:+.2f}%\n"

               f"🌟 超额收益 (Alpha): {metrics['alpha']:+.2f}%\n"

               f"🎯 胜率: {metrics['win_rate']:.2f}% | 盈亏比: {metrics['pnl_ratio']:.2f}\n"

               f"🛡️ 夏普: {metrics['sharpe_ratio']:.2f} | 索提诺: {metrics['sortino_ratio']:.2f}\n"

               f"📉 最大回撤: {metrics['max_drawdown']:.2f}% | 最长连亏: {metrics['max_consecutive_losses']} 次\n"

               f"🔄 交易动作数: {metrics['trade_count']} 次")

        res = QMessageBox.information(

            self,

            "测算成功",

            msg,

            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Ok

        )

        if res == QMessageBox.StandardButton.Save:

            self.save_current_as_report()



    def run_parameter_optimization(self):

        try:

            self.console_log.clear()

            self.console_error.clear()

            self.console_tabs.setCurrentIndex(0)

            self.right_tabs.setCurrentIndex(1)  # 保持在源码页查看日志

            self.append_log(">>> 准备启动多核并行参数寻优...\n")



            param_ranges = {

                'fast': range(5, 16, 2),

                'slow': range(20, 61, 5)

            }



            self.btn_optimize.setEnabled(False)



            self.opt_thread = OptimizerThread(

                self.input_code.text().strip(),

                self.source_viewer.toPlainText(),

                self.date_start.date().toString("yyyy-MM-dd"),

                self.date_end.date().toString("yyyy-MM-dd"),

                float(self.param_table.item(0, 1).text()),

                param_ranges

            )



            self.opt_thread.progress.connect(lambda p: self.btn_optimize.setText(f"寻优中 {p}%"))

            self.opt_thread.finished.connect(self.on_optimization_finished)

            self.opt_thread.start()

            self.append_log(">>> 寻优引擎启动成功，正在后台极速演算中...\n")



        except Exception as e:

            self.append_error(f"【主程序错误】启动参数寻优失败:\n{traceback.format_exc()}")

            self.btn_optimize.setEnabled(True)

            self.btn_optimize.setText("⚙️ 并行参数寻优")



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

        self.btn_save_as_new.setVisible(True)



    def edit_my_strategy(self, name):

        data = self.load_my_strategies()

        if name in data:

            self.current_editing_strategy = name

            self.lbl_desc.setText(f"🟢 正在编辑：【{name}】 (修改后请保存)")

            self.source_viewer.setPlainText(data[name].get('code'))

            self.source_viewer.setReadOnly(False)

            self.btn_save_code.setVisible(True)

            self.btn_save_as_new.setVisible(False)

            self.tabs.setCurrentIndex(0)

            self.right_tabs.setCurrentIndex(1)



    def save_current_code(self):

        if not self.current_editing_strategy: return

        data = self.load_my_strategies()

        data[self.current_editing_strategy]['code'] = self.source_viewer.toPlainText()

        self.save_my_strategies(data)

        QMessageBox.information(self, "成功", "源码已保存")



    def save_as_custom_strategy(self):

        current_code = self.source_viewer.toPlainText()

        while True:

            name, ok = QInputDialog.getText(self, "另存为自定义策略", "请输入策略名称:")

            if not ok:

                return

            if name.strip():

                data = self.load_my_strategies()

                key = name.strip()

                data[key] = {"desc": "基于系统策略修改", "code": current_code}

                self.save_my_strategies(data)

                self.refresh_my_strategies_list()

                QMessageBox.information(self, "成功", f"策略【{key}】已成功保存至自定义列表。")

                break

            QMessageBox.warning(self, "校验失败", "策略名称不能为空，请重新输入！")



    def export_report(self):

        if not self.last_metrics:

            return

        file_path, _ = QFileDialog.getSaveFileName(

            self, "保存报告", f"回测报告_{self.input_code.text()}.txt", "Text Files (*.txt)"

        )

        if not file_path:

            return

        with open(file_path, 'w', encoding='utf-8') as f:

            f.write("======= 量化策略回测报告 =======\n")

            f.write(f"标的代码: {self.input_code.text()}\n")

            f.write(f"测试时间: {self.date_start.date().toString('yyyy-MM-dd')} 至 {self.date_end.date().toString('yyyy-MM-dd')}\n")

            f.write("-" * 30 + "\n")

            f.write(f"总收益率: {self.last_metrics['total_return']:+.2f}%\n")

            f.write(f"最大回撤: {self.last_metrics['max_drawdown']:.2f}%\n")

            f.write(f"交易次数: {self.last_metrics['trade_count']}\n")

            f.write("-" * 30 + "\n")

            f.write("策略源码:\n")

            f.write(self.source_viewer.toPlainText())



        img_path = file_path.replace(".txt", ".png")

        self.chart.fig.savefig(img_path)

        QMessageBox.information(self, "成功", "报告与图表已保存")



    def load_my_strategies(self):

        if os.path.exists(self.my_strategies_file):

            with open(self.my_strategies_file, 'r', encoding='utf-8') as f:

                return json.load(f)

        return {}



    def save_my_strategies(self, data):

        os.makedirs(os.path.dirname(self.my_strategies_file), exist_ok=True)

        with open(self.my_strategies_file, 'w', encoding='utf-8') as f:

            json.dump(data, f, ensure_ascii=False, indent=4)



    def load_reports(self):

        if os.path.exists(self.reports_file):

            with open(self.reports_file, 'r', encoding='utf-8') as f:

                return json.load(f)

        return {}



    def save_reports(self, reports):

        os.makedirs(os.path.dirname(self.reports_file), exist_ok=True)

        with open(self.reports_file, 'w', encoding='utf-8') as f:

            json.dump(reports, f, ensure_ascii=False, indent=4)



    def refresh_reports_list(self):

        if not hasattr(self, 'report_layout'):

            return

        for i in reversed(range(self.report_layout.count())):

            w = self.report_layout.itemAt(i).widget()

            if w:

                w.setParent(None)

        reports = self.load_reports()

        for report_id in sorted(reports.keys(), reverse=True):

            self.report_layout.addWidget(ReportRow(reports[report_id], self))



    def save_current_as_report(self):

        if not self.last_run_data:

            return

        report_id = str(int(time.time() * 1000))

        reports = self.load_reports()

        reports[report_id] = {

            "id": report_id,

            "owner_id": Session.username or "guest",

            "title": f"未命名报告_{report_id[-4:]}",

            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),

            "conditions": {

                "strategy_name": self.last_run_data.get("strategy_name", "未知策略"),

                "code": self.last_run_data['code'],

                "capital": self.last_run_data['capital'],

                "start": self.last_run_data['start'],

                "end": self.last_run_data['end'],

                "quantity": self.param_table.item(2, 1).text() if self.param_table.item(2, 1) else "100"

            },

            "metrics": self.last_run_data['metrics'],

            "strategy_code": self.last_run_data['strategy_code'],

            "trades": self.last_run_data.get("trades", [])

        }

        self.save_reports(reports)

        self.refresh_reports_list()

        self.tabs.setCurrentWidget(self.reports_tab)

        QMessageBox.information(self, "成功", "已保存为回测报告。")



    def view_report_detail(self, report_id):

        reports = self.load_reports()

        report = reports.get(report_id)

        if not report:

            return

        if report.get('owner_id') != (Session.username or "guest"):

            QMessageBox.critical(self, "安全错误", "您无权查看此账户的回测报告！")

            return



        detail_win = QDialog(self)

        detail_win.setWindowTitle(f"回测详情 - {report.get('title', '未命名')}")

        detail_win.setMinimumSize(800, 600)

        layout = QVBoxLayout(detail_win)



        cond_box = QGroupBox("基础条件 (客观设定)")

        grid = QGridLayout(cond_box)

        c = report.get('conditions', {})

        grid.addWidget(QLabel(f"策略: {c.get('strategy_name', '--')}"), 0, 0)

        grid.addWidget(QLabel(f"股票代码: {c.get('code', '--')}"), 0, 1)

        grid.addWidget(QLabel(f"起始资金: {c.get('capital', '--')}"), 1, 0)

        grid.addWidget(QLabel(f"时间范围: {c.get('start', '--')} 至 {c.get('end', '--')}"), 1, 1)

        grid.addWidget(QLabel(f"单笔数量: {c.get('quantity', '100')}"), 2, 0)

        layout.addWidget(cond_box)



        metric_box = QGroupBox("评价指标 (性能表现)")

        m_layout = QHBoxLayout(metric_box)

        m = report.get('metrics', {})

        m_layout.addWidget(QLabel(f"总收益: {m.get('total_profit', 0):.2f}\n收益率: {m.get('total_return', 0):.2f}%"))

        m_layout.addWidget(QLabel(f"年化回报: {m.get('annual_return', 0):.2f}%\n夏普比率: {m.get('sharpe_ratio', 0):.2f}"))

        m_layout.addWidget(QLabel(f"最大回撤: {m.get('max_drawdown', 0):.2f}%\n交易次数: {m.get('trade_count', 0)}"))

        layout.addWidget(metric_box)



        log_view = QTableWidget()

        log_view.setColumnCount(4)

        log_view.setHorizontalHeaderLabels(["日期", "方向", "价格", "数量"])

        trades = report.get("trades", [])

        log_view.setRowCount(len(trades))

        for i, t in enumerate(trades):

            log_view.setItem(i, 0, QTableWidgetItem(str(t.get('date', '--'))))

            log_view.setItem(i, 1, QTableWidgetItem(str(t.get('type', '--'))))

            log_view.setItem(i, 2, QTableWidgetItem(f"{float(t.get('price', 0)):.2f}"))

            log_view.setItem(i, 3, QTableWidgetItem(str(t.get('amount', '--'))))

        layout.addWidget(log_view)



        code_box = QGroupBox("策略源码 (只读)")

        code_layout = QVBoxLayout(code_box)

        code_view = QPlainTextEdit()

        code_view.setReadOnly(True)

        code_view.setPlainText(report.get("strategy_code", ""))

        code_layout.addWidget(code_view)

        layout.addWidget(code_box)



        detail_win.exec()



    def on_edit_report_title(self, report_id):

        reports = self.load_reports()

        if report_id not in reports:

            return

        old_title = reports[report_id].get('title', '')

        while True:

            new_title, ok = QInputDialog.getText(self, "修改标题", "请输入新标题:", text=old_title)

            if not ok:

                return

            if new_title.strip():

                reports[report_id]['title'] = new_title.strip()

                self.save_reports(reports)

                self.refresh_reports_list()

                return

            QMessageBox.warning(self, "校验失败", "报告标题不能为空！")



    def on_delete_report(self, report_id):

        reply = QMessageBox.question(

            self, "确认删除", "确定要删除该回测报告吗？点击‘确定删除’后将无法恢复。",

            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No

        )

        if reply == QMessageBox.StandardButton.Yes:

            reports = self.load_reports()

            if report_id in reports:

                del reports[report_id]

                self.save_reports(reports)

                self.refresh_reports_list()



    def on_share_report(self, report_id):

        reports = self.load_reports()

        report = reports.get(report_id)

        if not report:

            return

        secret_key = "QUANT_PLATFORM_KEY"

        owner_id = Session.username or "guest"

        token = hashlib.md5(f"{report_id}{owner_id}{secret_key}".encode()).hexdigest()

        share_url = f"http://quant_system/share/report?id={report_id}&token={token}"

        QApplication.clipboard().setText(share_url)

        

        # 弹窗显示链接，点击后跳转

        dialog = QDialog(self)

        dialog.setWindowTitle("分享报告")

        layout = QVBoxLayout(dialog)

        label = QLabel(f"获取分享链接成功（已复制到剪贴板）：<br><br><a href='{share_url}'>{share_url}</a><br><br>点击链接跳转至消息页面")

        label.setTextFormat(Qt.TextFormat.RichText)

        label.setOpenExternalLinks(False)

        label.linkActivated.connect(lambda url: [dialog.accept(), self.jump_to_message_center()])

        layout.addWidget(label)

        dialog.exec()



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

        is_running_sim = False

        confirm_msg = f"确定要删除自定义策略【{name}】吗？"

        if is_running_sim:

            confirm_msg = f"⚠️ 警示：策略【{name}】正在执行模拟交易！\n" + confirm_msg

        reply = QMessageBox.question(

            self, "确认删除", confirm_msg,

            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No

        )

        if reply == QMessageBox.StandardButton.Yes:

            data = self.load_my_strategies()

            if name in data:

                del data[name]

                self.save_my_strategies(data)

                self.refresh_my_strategies_list()

                QMessageBox.information(self, "成功", "策略已删除且无法恢复。")



    def share_strategy(self, name):

        data = self.load_my_strategies().get(name)

        if data:

            secret_key = "STRATEGY_SECURE_2026"

            owner_id = Session.username or "guest"

            strategy_id = hashlib.sha1(name.encode()).hexdigest()[:10]

            token = hashlib.md5(f"{strategy_id}{owner_id}{secret_key}".encode()).hexdigest()

            share_url = f"http://quant_system/share/strategy?id={strategy_id}&token={token}"

            QApplication.clipboard().setText(share_url)

            

            dialog = QDialog(self)

            dialog.setWindowTitle("分享策略")

            layout = QVBoxLayout(dialog)

            label = QLabel(f"获取分享链接成功（已复制到剪贴板）：<br><br><a href='{share_url}'>{share_url}</a><br><br>点击链接跳转至消息页面")

            label.setTextFormat(Qt.TextFormat.RichText)

            label.setOpenExternalLinks(False)

            label.linkActivated.connect(lambda url: [dialog.accept(), self.jump_to_message_center()])

            layout.addWidget(label)

            dialog.exec()



    def jump_to_message_center(self):

        ""

        main_win = self.window()

        if hasattr(main_win, 'tabs'):

            for i in range(main_win.tabs.count()):

                if main_win.tabs.tabText(i) == "消息中心":

                    main_win.tabs.setCurrentIndex(i) # 执行跳转

                    break



    def run_my_strategy(self, name):

        self.edit_my_strategy(name)

        self.run_center_backtest()



    def on_backtest_error(self, msg):

        self.btn_run.setEnabled(True)

        self.btn_run.setText("▶ 执行单次测算")

        self.append_error(f"【底层报错弹窗】: {msg}")  # 同时记录到控制台

        QMessageBox.critical(self, "错误", msg)