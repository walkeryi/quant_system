# ui/backtest_tab.py
import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QGroupBox, QListWidget,
                             QFormLayout, QMessageBox, QSplitter, QTabWidget,
                             QPlainTextEdit, QInputDialog, QFileDialog, QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from datetime import datetime, timedelta

from ui.charts.backtest_chart import BacktestChart
from ui.threads.backtest_thread import BacktestThread
from config import CACHE_DIR

# 策略保存路径
STRATEGIES_FILE = os.path.join(CACHE_DIR, "custom_strategies.json")

# 为新手准备的预存示例算法库
DEFAULT_STRATEGIES = {
    "预存: 双均线策略 (5日/20日)": '''def generate_signals(df):
    """
    预存策略: 双均线策略
    当5日均线上穿20日均线时买入，下穿时卖出
    """
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()

    df['signal'] = 0
    df.loc[df['MA5'] > df['MA20'], 'signal'] = 1  
    df.loc[df['MA5'] <= df['MA20'], 'signal'] = -1 

    return df
''',
    "预存: 均值回归策略 (RSI)": '''def generate_signals(df):
    """
    预存策略: RSI 均值回归
    RSI < 30 买入 (超卖区域)
    RSI > 70 卖出 (超买区域)
    """
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


class BacktestTab(QWidget):
    """真正的专业级策略开发与回测工作台"""

    def __init__(self):
        super().__init__()
        self.strategies = {}
        self.last_backtest_result = None
        self.initUI()
        self.load_strategies()

    def initUI(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ================= 左侧：策略库管理器 =================
        left_panel = QWidget()
        left_panel.setMaximumWidth(260)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        list_group = QGroupBox("📚 策略中心")
        list_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; }")
        list_layout = QVBoxLayout(list_group)

        self.list_strategies = QListWidget()
        self.list_strategies.setStyleSheet("QListWidget { font-size: 13px; padding: 5px; }")
        self.list_strategies.itemClicked.connect(self.on_strategy_selected)
        list_layout.addWidget(self.list_strategies)

        btn_layout = QHBoxLayout()
        self.btn_new = QPushButton("➕ 新建")
        self.btn_del = QPushButton("🗑️ 删除")
        self.btn_share = QPushButton("🔗 分享")

        self.btn_new.clicked.connect(self.new_algorithm)
        self.btn_del.clicked.connect(self.delete_algorithm)
        self.btn_share.clicked.connect(self.share_algorithm)

        self.btn_share.setStyleSheet("color: #00e676;")
        self.btn_del.setStyleSheet("color: #ff5252;")

        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_del)
        btn_layout.addWidget(self.btn_share)
        list_layout.addLayout(btn_layout)

        left_layout.addWidget(list_group)

        # ================= 右侧：参数、源码与效益图 =================
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # --- 1. 右侧上方：回测运行参数 ---
        param_group = QGroupBox("⚙️ 回测运行参数设置")
        param_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; }")
        param_layout = QHBoxLayout(param_group)

        form1 = QFormLayout()
        self.input_code = QLineEdit("000001")
        self.input_capital = QLineEdit("100000")
        form1.addRow("标的代码:", self.input_code)
        form1.addRow("初始资金:", self.input_capital)

        form2 = QFormLayout()
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=365)
        self.input_start = QLineEdit(start_dt.strftime("%Y-%m-%d"))
        self.input_end = QLineEdit(end_dt.strftime("%Y-%m-%d"))
        form2.addRow("开始日期:", self.input_start)
        form2.addRow("结束日期:", self.input_end)

        form3 = QFormLayout()
        self.input_stop_loss = QLineEdit("5.0")
        form3.addRow("止损幅度(%):", self.input_stop_loss)

        self.btn_run = QPushButton("▶ 启动策略回测")
        self.btn_run.setFixedHeight(45)
        self.btn_run.setStyleSheet("""
            QPushButton { background-color: #e53935; color: white; font-size: 15px; font-weight: bold; border-radius: 4px; padding: 0 20px; }
            QPushButton:hover { background-color: #f44336; }
            QPushButton:disabled { background-color: #555555; color: #888888; }
        """)
        self.btn_run.clicked.connect(self.run_backtest)

        param_layout.addLayout(form1)
        param_layout.addLayout(form2)
        param_layout.addLayout(form3)
        param_layout.addStretch()
        param_layout.addWidget(self.btn_run)

        right_layout.addWidget(param_group)

        # --- 2. 右侧下方核心：带有切换按钮的 Tab 页面 ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { padding: 10px 30px; font-size: 15px; font-weight: bold; }
            QTabBar::tab:selected { color: #2196F3; }
        """)

        # 【Tab 1: 策略源码】
        code_tab = QWidget()
        code_layout = QVBoxLayout(code_tab)

        self.code_editor = QPlainTextEdit()
        font = QFont("Consolas", 12)
        self.code_editor.setFont(font)
        self.code_editor.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; padding: 10px; border-radius: 5px;")
        self.code_editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.btn_save = QPushButton("💾 保存 / 更新当前源码")
        self.btn_save.setFixedHeight(35)
        self.btn_save.setStyleSheet(
            "background-color: #4CAF50; color: white; font-size: 14px; font-weight: bold; border-radius: 4px;")
        self.btn_save.clicked.connect(self.save_algorithm)

        code_layout.addWidget(self.code_editor)
        code_layout.addWidget(self.btn_save)
        self.tabs.addTab(code_tab, "💻 策略源码")

        # 【Tab 2: 回测效益图】
        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)

        # 结果统计数据条
        res_layout = QHBoxLayout()
        self.lbl_returns = QLabel("总收益率: --")
        self.lbl_drawdown = QLabel("最大回撤: --")
        self.lbl_trades = QLabel("交易次数: --")
        self.lbl_final_cash = QLabel("期末资产: --")

        for lbl in [self.lbl_returns, self.lbl_drawdown, self.lbl_trades, self.lbl_final_cash]:
            lbl.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
            res_layout.addWidget(lbl)

        res_layout.addStretch()
        self.btn_export = QPushButton("📥 导出报告")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.save_backtest_report)
        res_layout.addWidget(self.btn_export)

        chart_layout.addLayout(res_layout)

        self.chart = BacktestChart()
        chart_layout.addWidget(self.chart.canvas)

        self.tabs.addTab(chart_tab, "📈 回测效益图")

        right_layout.addWidget(self.tabs)

        # 组装主分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([260, 1000])

        main_layout.addWidget(splitter)

    # ================= 策略管理逻辑 =================
    def load_strategies(self):
        """加载预存策略与自定义策略"""
        self.strategies = DEFAULT_STRATEGIES.copy()
        if os.path.exists(STRATEGIES_FILE):
            try:
                with open(STRATEGIES_FILE, 'r', encoding='utf-8') as f:
                    custom = json.load(f)
                    for k, v in custom.items():
                        prefix_name = f"自定义: {k}" if not k.startswith("自定义:") else k
                        self.strategies[prefix_name] = v
            except Exception:
                pass

        self.list_strategies.clear()
        self.list_strategies.addItems(list(self.strategies.keys()))

        # 默认选中第一条
        if self.list_strategies.count() > 0:
            self.list_strategies.setCurrentRow(0)
            self.on_strategy_selected(self.list_strategies.item(0))

    def on_strategy_selected(self, item):
        """点击列表项切换策略内容"""
        strategy_name = item.text()
        if strategy_name in self.strategies:
            self.code_editor.setPlainText(self.strategies[strategy_name])

            # 权限控制：预存策略不可分享和删除，且只能另存为
            if strategy_name.startswith("预存:"):
                self.btn_del.setEnabled(False)
                self.btn_share.setEnabled(False)
                self.btn_save.setText("另存为自定义策略")
                self.btn_save.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
            else:
                self.btn_del.setEnabled(True)
                self.btn_share.setEnabled(True)
                self.btn_save.setText("💾 保存 / 更新源码")
                self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

            # 自动跳回源码查看 Tab
            self.tabs.setCurrentIndex(0)

    def new_algorithm(self):
        """完全自主编写新策略"""
        self.code_editor.setPlainText('''def generate_signals(df):
    """
    在这里编写您的自定义量化交易策略
    """
    df['signal'] = 0
    # TODO: 编写买卖逻辑

    return df
''')
        self.tabs.setCurrentIndex(0)
        self.list_strategies.clearSelection()
        self.btn_save.setText("💾 保存为自定义策略")
        self.btn_save.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")

    def save_algorithm(self):
        """保存或更新策略逻辑"""
        code = self.code_editor.toPlainText()
        current_item = self.list_strategies.currentItem()
        strategy_name = current_item.text() if current_item else ""

        if not strategy_name or strategy_name.startswith("预存:"):
            name, ok = QInputDialog.getText(self, "保存策略", "请输入自定义策略的名称:")
            if ok and name:
                clean_name = name.replace("预存:", "").replace("自定义:", "").strip()
                if not clean_name: return
                save_name = f"自定义: {clean_name}"
                self._write_strategy_to_disk(save_name, code)
                QMessageBox.information(self, "成功", f"【{save_name}】创建成功！")
        else:
            self._write_strategy_to_disk(strategy_name, code)
            QMessageBox.information(self, "成功", f"【{strategy_name}】源码已更新！")

    def _write_strategy_to_disk(self, name, code):
        custom_strats = {}
        if os.path.exists(STRATEGIES_FILE):
            with open(STRATEGIES_FILE, 'r', encoding='utf-8') as f:
                custom_strats = json.load(f)

        custom_strats[name] = code
        with open(STRATEGIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(custom_strats, f, ensure_ascii=False, indent=4)

        self.load_strategies()
        # 重新定位到刚保存的项
        items = self.list_strategies.findItems(name, Qt.MatchFlag.MatchExactly)
        if items:
            self.list_strategies.setCurrentItem(items[0])
            self.on_strategy_selected(items[0])

    def delete_algorithm(self):
        """删除自定义策略"""
        current_item = self.list_strategies.currentItem()
        if not current_item: return
        name = current_item.text()

        reply = QMessageBox.question(self, "确认删除", f"确定要永久删除 【{name}】 吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if os.path.exists(STRATEGIES_FILE):
                with open(STRATEGIES_FILE, 'r', encoding='utf-8') as f:
                    custom_strats = json.load(f)
                if name in custom_strats:
                    del custom_strats[name]
                    with open(STRATEGIES_FILE, 'w', encoding='utf-8') as f:
                        json.dump(custom_strats, f, ensure_ascii=False, indent=4)
                    QMessageBox.information(self, "成功", "策略已删除！")
                    self.load_strategies()

    def share_algorithm(self):
        """分享自定义策略"""
        current_item = self.list_strategies.currentItem()
        if not current_item: return
        name = current_item.text()
        code = self.code_editor.toPlainText()

        share_token = f"!!QUANT_SHARE_{hash(code) % 1000000}!!"
        clipboard = QApplication.clipboard()
        clipboard.setText(f"我正在使用量化系统分享策略【{name}】，\n分享口令：{share_token}\n源码如下：\n{code}")
        QMessageBox.information(self, "分享成功",
                                f"【{name}】分享口令已生成并复制到系统剪贴板！\n您可以直接粘贴发送给朋友。")

    # ================= 运行回测与报告生成 =================
    def run_backtest(self):
        code = self.input_code.text().strip()
        start_date = self.input_start.text().strip()
        end_date = self.input_end.text().strip()
        custom_code = self.code_editor.toPlainText()

        try:
            capital = float(self.input_capital.text().strip())
            stop_loss = float(self.input_stop_loss.text().strip())
        except ValueError:
            QMessageBox.warning(self, "参数错误", "资金和止损幅度必须是数字！")
            return

        if not code:
            QMessageBox.warning(self, "参数错误", "请输入股票代码！")
            return

        # 准备执行，自动切回效益图 Tab，并展示等待状态
        self.tabs.setCurrentIndex(1)
        self.btn_run.setEnabled(False)
        self.btn_run.setText("⏳ 测算运行中...")
        self.btn_export.setEnabled(False)

        current_item = self.list_strategies.currentItem()
        strategy_name = current_item.text() if current_item else "未命名策略"

        self.last_backtest_result = {
            'code': code, 'strategy': strategy_name,
            'start': start_date, 'end': end_date, 'capital': capital, 'stop_loss': stop_loss
        }

        self.thread = BacktestThread(code, custom_code, start_date, end_date, capital, stop_loss)
        self.thread.finished.connect(self.on_backtest_finished)
        self.thread.error.connect(self.on_backtest_error)
        self.thread.start()

    def on_backtest_finished(self, df, equity_df, trades, metrics):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("▶ 启动策略回测")

        self.last_backtest_result['metrics'] = metrics
        self.last_backtest_result['trades'] = trades
        self.btn_export.setEnabled(True)

        ret = metrics['total_return']
        self.lbl_returns.setText(f"总收益率: {ret:+.2f}%")
        self.lbl_returns.setStyleSheet(
            f"font-size: 14px; font-weight: bold; padding: 5px; color: {'#ff5252' if ret > 0 else '#00e676'};")
        self.lbl_drawdown.setText(f"最大回撤: {metrics['max_drawdown']:.2f}%")
        self.lbl_trades.setText(f"交易次数: {metrics['trade_count']} 次")
        self.lbl_final_cash.setText(f"期末资产: {metrics['final_equity']:,.2f} 元")

        # 将数据丢给图表画图
        self.chart.draw(df, equity_df, trades)

    def on_backtest_error(self, err_msg):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("▶ 启动策略回测")
        self.tabs.setCurrentIndex(0)  # 报错就跳回代码页面方便改 BUG
        self.btn_export.setEnabled(False)
        QMessageBox.critical(self, "回测中断", err_msg)

    def save_backtest_report(self):
        """保存回测结果为本地 TXT 报告"""
        if not self.last_backtest_result: return

        data = self.last_backtest_result
        default_name = f"回测报告_{data['code']}_{datetime.now().strftime('%Y%m%d%H%M')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(self, "保存回测报告", default_name, "Text Files (*.txt)")

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("=" * 50 + "\n")
                    f.write("量化智能策略回测报告\n")
                    f.write("=" * 50 + "\n\n")

                    f.write("【基本参数】\n")
                    f.write(f"测试标的: {data['code']}\n")
                    f.write(f"使用策略: {data['strategy']}\n")
                    f.write(f"时间范围: {data['start']} 至 {data['end']}\n")
                    f.write(f"初始资金: {data['capital']} 元\n")
                    f.write(f"止损幅度: {data['stop_loss']}%\n\n")

                    m = data['metrics']
                    f.write("【表现评估】\n")
                    f.write(f"期末资产: {m['final_equity']:.2f} 元\n")
                    f.write(f"总收益率: {m['total_return']:.2f}%\n")
                    f.write(f"最大回撤: {m['max_drawdown']:.2f}%\n")
                    f.write(f"交易总次数: {m['trade_count']} 次\n\n")

                    f.write("【交易明细记录】\n")
                    for t in data['trades']:
                        f.write(
                            f"[{t['date']}] 动作:{'买入' if t['type'] == 'buy' else '卖出'} | 成交价:{t['price']:.2f} | 数量:{t['amount']}股\n")

                QMessageBox.information(self, "成功", f"回测报告已成功保存至:\n{file_path}")
            except Exception as e:
                QMessageBox.warning(self, "保存失败", f"无法写入文件:\n{str(e)}")