# ui/quant_backtest_tab.py
import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
                             QPushButton, QLineEdit, QGroupBox, QHeaderView,
                             QFormLayout, QMessageBox, QSplitter, QTabWidget, QTableWidgetItem,
                             QPlainTextEdit, QDateEdit, QScrollArea, QFrame, QInputDialog)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from ui.charts.backtest_chart import BacktestChart
from ui.threads.backtest_thread import BacktestThread

# 真实的量化代码库
STRATEGY_CENTER_DATA = {
    "双均线金叉策略": {
        "desc": "经典趋势跟踪策略 (5日均线上穿20日均线买入)",
        "code": '''def generate_signals(df):
    # 真实可运行: 双均线策略
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
    # 真实可运行: RSI 震荡策略
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
    """'我的策略' 列表中的一行自定义交互组件"""

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
        self.btn_trade = QPushButton("⚡ 实盘")
        self.btn_set = QPushButton("⚙️ 编辑源码")
        self.btn_rename = QPushButton("✏️ 重命名")
        self.btn_clone = QPushButton("📄 克隆")
        self.btn_del = QPushButton("🗑️ 删除")

        self.btn_trade.setStyleSheet(btn_style + "QPushButton { color: #ff5252; font-weight: bold; }")
        self.btn_sim.setStyleSheet(btn_style + "QPushButton { color: #00e676; font-weight: bold; }")

        # 绑定真实的事件互动 (注意使用 lambda checked, n=name 解决闭包变量延迟绑定问题)
        self.btn_sim.clicked.connect(lambda checked, n=name: parent_tab.run_my_strategy(n))
        self.btn_trade.clicked.connect(
            lambda: QMessageBox.information(self, "提示", "实盘交易功能正在接入券商通道，敬请期待！"))
        self.btn_set.clicked.connect(lambda checked, n=name: parent_tab.edit_my_strategy(n))
        self.btn_rename.clicked.connect(lambda checked, n=name: parent_tab.rename_my_strategy(n))
        self.btn_clone.clicked.connect(lambda checked, n=name: parent_tab.clone_my_strategy(n))
        self.btn_del.clicked.connect(lambda checked, n=name: parent_tab.delete_my_strategy(n))

        for btn in [self.btn_sim, self.btn_trade, self.btn_set, self.btn_rename, self.btn_clone, self.btn_del]:
            if btn not in [self.btn_sim, self.btn_trade]:
                btn.setStyleSheet(btn_style)
            layout.addWidget(btn)


class QuantBacktestTab(QWidget):
    def __init__(self):
        super().__init__()
        self.my_strategies_file = "quant_system/cache/my_strategies.json"
        self.current_editing_strategy = None  # 记录当前正在编辑器里修改的是哪个自定义策略
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
        """策略中心：三图展示 + 源码 + 参数配置"""
        layout = QHBoxLayout(self.center_tab)

        # 1. 左侧策略选择列表
        self.center_list = QTableWidget(len(STRATEGY_CENTER_DATA), 1)
        self.center_list.setMaximumWidth(220)
        self.center_list.setHorizontalHeaderLabels(["可选策略库"])
        self.center_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.center_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.center_list.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for i, name in enumerate(STRATEGY_CENTER_DATA.keys()):
            self.center_list.setItem(i, 0, QTableWidgetItem(name))

        self.center_list.itemSelectionChanged.connect(self.on_strategy_selected)
        layout.addWidget(self.center_list)

        # 2. 右侧大区：参数配置与三图并列
        right_panel = QVBoxLayout()

        # 顶部操作栏
        param_bar = QHBoxLayout()

        self.input_code = QLineEdit("000001")
        self.input_code.setFixedWidth(80)
        self.input_code.setPlaceholderText("标的代码")

        self.date_start = QDateEdit(QDate.currentDate().addYears(-1))
        self.date_start.setCalendarPopup(True)
        self.date_end = QDateEdit(QDate.currentDate())
        self.date_end.setCalendarPopup(True)

        param_bar.addWidget(QLabel("代码:"))
        param_bar.addWidget(self.input_code)
        param_bar.addWidget(QLabel(" 开始日期:"))
        param_bar.addWidget(self.date_start)
        param_bar.addWidget(QLabel(" 结束日期:"))
        param_bar.addWidget(self.date_end)
        param_bar.addStretch()

        # 核心运行按钮
        self.btn_run = QPushButton("▶ 运行当前源码测算")
        self.btn_run.setStyleSheet(
            "background-color: #e53935; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")
        self.btn_run.clicked.connect(self.run_center_backtest)

        self.btn_clone_center = QPushButton("⬇ 克隆到我的策略")
        self.btn_clone_center.setStyleSheet(
            "background-color: #2196F3; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")
        self.btn_clone_center.clicked.connect(self.clone_to_my_strategy)

        param_bar.addWidget(self.btn_run)
        param_bar.addWidget(self.btn_clone_center)
        right_panel.addLayout(param_bar)

        # 中间：三图展示区 + 参数表格
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        chart_area = QWidget()
        chart_layout = QVBoxLayout(chart_area)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart = BacktestChart()
        chart_layout.addWidget(self.chart.canvas)

        self.param_table = QTableWidget(4, 2)
        self.param_table.setHorizontalHeaderLabels(["参数名", "当前配置"])
        self.param_table.setFixedWidth(220)
        self.param_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        param_items = [("初始资金", "100000"), ("交易费率", "0.0003"), ("滑点", "0.01"), ("止损点(%)", "5.0")]
        for i, (k, v) in enumerate(param_items):
            self.param_table.setItem(i, 0, QTableWidgetItem(k))
            self.param_table.setItem(i, 1, QTableWidgetItem(v))

        content_splitter.addWidget(chart_area)
        content_splitter.addWidget(self.param_table)
        content_splitter.setSizes([800, 220])
        right_panel.addWidget(content_splitter)

        # 底部：源码展示区
        source_group = QGroupBox("策略描述与源码查看")
        source_group.setFixedHeight(220)
        source_layout = QVBoxLayout(source_group)
        source_layout.setContentsMargins(5, 10, 5, 5)

        # 标题与保存按钮栏
        source_header_layout = QHBoxLayout()
        self.lbl_desc = QLabel("策略描述：请在左侧选择策略...")
        self.lbl_desc.setStyleSheet("color: #aaaaaa; font-weight: bold;")

        self.btn_save_code = QPushButton("💾 保存对当前策略的修改")
        self.btn_save_code.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; border-radius: 3px; padding: 4px 15px;")
        self.btn_save_code.setVisible(False)  # 默认隐藏，只有编辑自定义策略时显示
        self.btn_save_code.clicked.connect(self.save_current_code)

        source_header_layout.addWidget(self.lbl_desc)
        source_header_layout.addStretch()
        source_header_layout.addWidget(self.btn_save_code)
        source_layout.addLayout(source_header_layout)

        self.source_viewer = QPlainTextEdit()
        self.source_viewer.setReadOnly(True)
        self.source_viewer.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas; font-size: 14px; border: 1px solid #333; padding: 5px;")
        source_layout.addWidget(self.source_viewer)

        right_panel.addWidget(source_group)
        layout.addLayout(right_panel)

        # 默认选中第一条系统策略
        self.center_list.setCurrentCell(0, 0)

    def initMyStrategyTab(self):
        """我的策略：真实动态加载列表"""
        layout = QVBoxLayout(self.my_strategy_tab)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        self.btn_new = QPushButton("+ 新建空白策略")
        self.btn_new.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px;")
        self.btn_new.clicked.connect(self.create_new_strategy)
        toolbar.addWidget(self.btn_new)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 策略列表滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #1e1e1e; }")
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.list_container)
        layout.addWidget(scroll)

        # 初始化加载真实数据
        self.refresh_my_strategies_list()

    # ================= 本地数据持久化管理 =================
    def load_my_strategies(self):
        if os.path.exists(self.my_strategies_file):
            try:
                with open(self.my_strategies_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_my_strategies(self, data):
        os.makedirs(os.path.dirname(self.my_strategies_file), exist_ok=True)
        with open(self.my_strategies_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def refresh_my_strategies_list(self):
        """刷新我的策略UI列表"""
        # 清空现有部件
        for i in reversed(range(self.list_layout.count())):
            widget = self.list_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 从 JSON 加载并渲染
        data = self.load_my_strategies()
        for name in data.keys():
            row = StrategyRow(name, self)
            self.list_layout.addWidget(row)

    # ================= 我的策略 - 按钮核心功能 =================
    def create_new_strategy(self):
        name, ok = QInputDialog.getText(self, "新建策略", "给您的新策略起个霸气的名字:")
        if ok and name.strip():
            name = name.strip()
            data = self.load_my_strategies()
            if name in data:
                QMessageBox.warning(self, "错误", "策略名称已存在！")
                return

            # 写入默认空白模板
            data[name] = {
                "desc": "自定义策略",
                "code": "def generate_signals(df):\n    # TODO: 在此编写您的自定义逻辑\n    df['signal'] = 0\n    return df\n"
            }
            self.save_my_strategies(data)
            self.refresh_my_strategies_list()

            # 自动跳转并打开编辑
            self.edit_my_strategy(name)

    def delete_my_strategy(self, name):
        reply = QMessageBox.question(self, "确认删除", f"⚠️ 确定要永久删除策略【{name}】吗？不可恢复！",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            data = self.load_my_strategies()
            if name in data:
                del data[name]
                self.save_my_strategies(data)
                self.refresh_my_strategies_list()

                # 如果删掉的正好是当前在编辑的，清空编辑器
                if self.current_editing_strategy == name:
                    self.current_editing_strategy = None
                    self.lbl_desc.setText("策略描述：请在左侧选择策略...")
                    self.source_viewer.setPlainText("")
                    self.source_viewer.setReadOnly(True)
                    self.btn_save_code.setVisible(False)

    def rename_my_strategy(self, old_name):
        new_name, ok = QInputDialog.getText(self, "重命名策略", "请输入新名称:", text=old_name)
        if ok and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            data = self.load_my_strategies()
            if new_name in data:
                QMessageBox.warning(self, "错误", "策略名称已被占用！")
                return

            # 更新字典键名
            data[new_name] = data.pop(old_name)
            self.save_my_strategies(data)
            self.refresh_my_strategies_list()

            if self.current_editing_strategy == old_name:
                self.current_editing_strategy = new_name
                self.lbl_desc.setText(f"当前正在编辑自定义策略：【{new_name}】")

    def clone_my_strategy(self, name):
        """克隆自定义策略"""
        data = self.load_my_strategies()
        if name in data:
            new_name = f"{name}_副本"
            data[new_name] = data[name].copy()
            self.save_my_strategies(data)
            self.refresh_my_strategies_list()

    def edit_my_strategy(self, name):
        """将自定义策略加载到前台进行查看或修改"""
        data = self.load_my_strategies()
        if name in data:
            self.current_editing_strategy = name
            self.lbl_desc.setText(f"🟢 当前正在自由编辑：【{name}】 (修改后请务必点击右侧保存)")
            self.source_viewer.setPlainText(data[name].get('code', ''))

            # 开启编辑权限
            self.source_viewer.setReadOnly(False)
            self.source_viewer.setStyleSheet(
                "background-color: #1e1e1e; color: #00e676; font-family: Consolas; font-size: 14px; border: 1px solid #4CAF50; padding: 5px;")
            self.btn_save_code.setVisible(True)

            # 解除系统策略的焦点
            self.center_list.clearSelection()
            # 自动跳转回策略中心图表页
            self.tabs.setCurrentIndex(0)

    def run_my_strategy(self, name):
        """一键执行我的策略"""
        self.edit_my_strategy(name)
        self.run_center_backtest()

    # ================= 联动与保存机制 =================
    def on_strategy_selected(self):
        """当用户点击左侧的【系统内置策略】时"""
        current_row = self.center_list.currentRow()
        if current_row >= 0:
            item = self.center_list.item(current_row, 0)
            strategy_name = item.text()
            data = STRATEGY_CENTER_DATA.get(strategy_name, {})

            self.current_editing_strategy = None  # 标记为系统策略
            self.lbl_desc.setText(f"🔒 系统只读策略：{data.get('desc', '无')} (若需修改请先克隆)")
            self.source_viewer.setPlainText(data.get('code', ''))

            # 关闭编辑权限
            self.source_viewer.setReadOnly(True)
            self.source_viewer.setStyleSheet(
                "background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas; font-size: 14px; border: 1px solid #333; padding: 5px;")
            self.btn_save_code.setVisible(False)

    def clone_to_my_strategy(self):
        """将当前编辑器内的代码保存为新的私人策略"""
        code = self.source_viewer.toPlainText()
        if not code.strip():
            return

        name, ok = QInputDialog.getText(self, "另存为我的策略", "为这个策略配置起个名字:")
        if ok and name.strip():
            name = name.strip()
            data = self.load_my_strategies()
            data[name] = {"desc": "脱胎于系统的自定义策略", "code": code}
            self.save_my_strategies(data)
            self.refresh_my_strategies_list()
            QMessageBox.information(self, "成功", f"策略【{name}】已成功加入「我的策略」！")

            # 自动转入编辑模式
            self.edit_my_strategy(name)

    def save_current_code(self):
        """更新正在编辑的私人策略代码"""
        if self.current_editing_strategy:
            code = self.source_viewer.toPlainText()
            data = self.load_my_strategies()
            if self.current_editing_strategy in data:
                data[self.current_editing_strategy]['code'] = code
                self.save_my_strategies(data)
                QMessageBox.information(self, "保存成功", f"【{self.current_editing_strategy}】的源码修改已保存至本地！")
        else:
            # 防御性代码，理论上系统策略状态下按钮是隐藏的
            self.clone_to_my_strategy()

    # ================= 核心测算执行逻辑 =================
    def run_center_backtest(self):
        code = self.input_code.text().strip()
        start_date = self.date_start.date().toString("yyyy-MM-dd")
        end_date = self.date_end.date().toString("yyyy-MM-dd")

        # 无论系统还是自定义，直接抓取当前编辑器里的内容跑回测
        strategy_code = self.source_viewer.toPlainText()

        if not code:
            QMessageBox.warning(self, "错误", "请输入交易标的代码！")
            return

        try:
            capital = float(self.param_table.item(0, 1).text())
            stop_loss = float(self.param_table.item(3, 1).text())
        except Exception:
            QMessageBox.warning(self, "参数错误", "参数表格中的数据格式不正确！")
            return

        self.btn_run.setEnabled(False)
        self.btn_run.setText("⏳ 测算运行中...")

        self.thread = BacktestThread(code, strategy_code, start_date, end_date, capital, stop_loss)
        self.thread.finished.connect(self.on_backtest_finished)
        self.thread.error.connect(self.on_backtest_error)
        self.thread.start()

    def on_backtest_finished(self, df, equity_df, trades, metrics):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("▶ 运行当前源码测算")

        self.chart.draw(df, equity_df, trades)
        ret = metrics['total_return']
        QMessageBox.information(self, "测算完成",
                                f"回测执行完毕！\n"
                                f"总收益率: {ret:+.2f}%\n"
                                f"最大回撤: {metrics['max_drawdown']:.2f}%\n"
                                f"交易次数: {metrics['trade_count']} 次")

    def on_backtest_error(self, err_msg):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("▶ 运行当前源码测算")
        QMessageBox.critical(self, "回测中断", err_msg)