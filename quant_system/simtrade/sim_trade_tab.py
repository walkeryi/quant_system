# -*- coding: utf-8 -*-
"""
模拟交易 Tab
"""
import json
import os
import time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
                             QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
                             QInputDialog, QDialog, QFormLayout, QComboBox, QHeaderView,
                             QPlainTextEdit, QLineEdit, QDoubleSpinBox, QSpinBox)
from PyQt6.QtCore import Qt

from quant_system.data.storage import StateManager


class CreateTradeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建模拟交易")
        self.setMinimumWidth(400)
        self.strategies = self.load_all_strategies()
        self.initUI()

    def load_all_strategies(self):
        from quant_system.backtest import STRATEGY_CENTER_DATA
        all_strategies = {}
        for k, v in STRATEGY_CENTER_DATA.items():
            all_strategies[k] = v['code']
        custom_file = "quant_system/cache/my_strategies.json"
        if os.path.exists(custom_file):
            with open(custom_file, 'r', encoding='utf-8') as f:
                custom_data = json.load(f)
                for k, v in custom_data.items():
                    all_strategies[f"(自定义) {k}"] = v.get('code', '')
        return all_strategies

    def initUI(self):
        layout = QFormLayout(self)
        self.combo_strategy = QComboBox()
        self.combo_strategy.addItems(list(self.strategies.keys()))
        layout.addRow("选择策略:", self.combo_strategy)

        self.input_code = QLineEdit("000001")
        layout.addRow("股票代码:", self.input_code)

        self.spin_capital = QDoubleSpinBox()
        self.spin_capital.setRange(1000, 100000000)
        self.spin_capital.setValue(100000)
        layout.addRow("起始资金:", self.spin_capital)

        self.spin_volume = QSpinBox()
        self.spin_volume.setRange(100, 1000000)
        self.spin_volume.setSingleStep(100)
        self.spin_volume.setValue(100)
        layout.addRow("每次交易数量:", self.spin_volume)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("确定")
        btn_cancel = QPushButton("取消")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)

    def get_data(self):
        s_name = self.combo_strategy.currentText()
        return {
            "strategy_name": s_name,
            "strategy_code": self.strategies.get(s_name, ""),
            "code": self.input_code.text().strip(),
            "capital": self.spin_capital.value(),
            "volume": self.spin_volume.value()
        }


class SimTradeTab(QWidget):
    def __init__(self):
        super().__init__()
        self.engine = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        ctrl_layout = QHBoxLayout()
        self.btn_create = QPushButton("创建交易")
        self.btn_view = QPushButton("查看策略")
        self.btn_change = QPushButton("更换策略")
        self.btn_end = QPushButton("结束交易")
        self.btn_history = QPushButton("历史记录")

        for btn in [self.btn_create, self.btn_view, self.btn_change, self.btn_end, self.btn_history]:
            btn.setStyleSheet("padding: 6px 12px; font-weight: bold;")
            ctrl_layout.addWidget(btn)
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        info_layout = QHBoxLayout()

        self.group_base = QGroupBox("基础条件")
        base_v = QVBoxLayout(self.group_base)
        self.lbl_base = QLabel("当前无运行中的模拟交易")
        base_v.addWidget(self.lbl_base)

        self.group_metrics = QGroupBox("评价指标")
        met_v = QVBoxLayout(self.group_metrics)
        self.lbl_metrics = QLabel("收益率: -- | 夏普: -- | 回撤: --")
        met_v.addWidget(self.lbl_metrics)

        info_layout.addWidget(self.group_base, 1)
        info_layout.addWidget(self.group_metrics, 1)
        layout.addLayout(info_layout)

        layout.addWidget(QLabel("建议记录"))
        self.table_logs = QTableWidget(0, 4)
        self.table_logs.setHorizontalHeaderLabels(["时间", "动作", "价格", "说明"])
        self.table_logs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_logs)

        self.btn_create.clicked.connect(self.on_create_trade)
        self.btn_view.clicked.connect(self.on_view_strategy)
        self.btn_change.clicked.connect(self.on_change_strategy)
        self.btn_end.clicked.connect(self.on_end_trade)
        self.btn_history.clicked.connect(self.show_history)

    def on_create_trade(self):
        if self._is_running():
            QMessageBox.warning(self, "警告", "当前已有模拟交易在运行，请先结束！")
            return

        dialog = CreateTradeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['code']:
                QMessageBox.warning(self, "校验失败", "股票代码不能为空！")
                return

            state = {
                "is_running": True,
                "code": data['code'],
                "capital": data['capital'],
                "volume": data['volume'],
                "strategy_name": data['strategy_name'],
                "strategy_code": data['strategy_code'],
                "start_time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            StateManager.save_sim_state(state)

            QMessageBox.information(self, "成功", "模拟交易已启动！")
            self.refresh_ui()
            self.start_engine()

    def on_view_strategy(self):
        if not self._is_running():
            QMessageBox.information(self, "提示", "当前无运行中的模拟交易！")
            return

        state = StateManager.load_sim_state()
        dialog = QDialog(self)
        dialog.setWindowTitle(f"当前策略源码 - {state.get('strategy_name', '')}")
        dialog.setMinimumSize(600, 400)
        layout = QVBoxLayout(dialog)
        viewer = QPlainTextEdit()
        viewer.setReadOnly(True)
        viewer.setPlainText(state.get('strategy_code', '无代码'))
        layout.addWidget(viewer)
        dialog.exec()

    def on_change_strategy(self):
        if not self._is_running():
            QMessageBox.information(self, "提示", "当前无运行中的模拟交易！")
            return

        state = StateManager.load_sim_state()
        dialog = CreateTradeDialog(self)
        dialog.setWindowTitle("更换策略")
        dialog.input_code.setText(state['code'])
        dialog.input_code.setEnabled(False)
        dialog.spin_capital.setValue(state['capital'])
        dialog.spin_capital.setEnabled(False)
        dialog.spin_volume.setValue(state.get('volume', 100))

        idx = dialog.combo_strategy.findText(state.get('strategy_name', ''))
        if idx >= 0:
            dialog.combo_strategy.setCurrentIndex(idx)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            state.update({
                'strategy_name': data['strategy_name'],
                'strategy_code': data['strategy_code'],
                'volume': data['volume']
            })
            StateManager.save_sim_state(state)
            QMessageBox.information(self, "成功", "策略配置已热更新！")
            self.refresh_ui()

    def on_end_trade(self):
        if not self._is_running():
            QMessageBox.information(self, "提示", "当前没有正在运行的模拟交易。")
            return

        reply = QMessageBox.question(self, "确认", "确定要结束本轮模拟交易吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            state = StateManager.load_sim_state()
            state['is_running'] = False
            state['end_time'] = time.strftime("%Y-%m-%d %H:%M:%S")
            StateManager.append_sim_history(state)
            StateManager.save_sim_state({"is_running": False})
            self.stop_engine()
            self.refresh_ui()

    def show_history(self):
        history = StateManager.get_sim_history()
        if not history:
            return QMessageBox.information(self, "历史记录", "暂无历史交易记录。")

        dialog = QDialog(self)
        dialog.setWindowTitle("模拟交易历史归档")
        dialog.setMinimumSize(800, 500)
        layout = QVBoxLayout(dialog)

        table = QTableWidget(len(history), 6)
        table.setHorizontalHeaderLabels(["启动时间", "结束时间", "策略名称", "标的", "初始资金", "最后状态"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for i, record in enumerate(reversed(history)):
            table.setItem(i, 0, QTableWidgetItem(record.get('start_time', '--')))
            table.setItem(i, 1, QTableWidgetItem(record.get('end_time', '--')))
            table.setItem(i, 2, QTableWidgetItem(record.get('strategy_name', '--')))
            table.setItem(i, 3, QTableWidgetItem(record.get('code', '--')))
            table.setItem(i, 4, QTableWidgetItem(str(record.get('capital', '--'))))
            table.setItem(i, 5, QTableWidgetItem("已结束"))

        layout.addWidget(table)
        dialog.exec()

    def refresh_ui(self):
        if self._is_running():
            state = StateManager.load_sim_state()
            self.lbl_base.setText(f"标的: {state['code']} | 初始资金: {state['capital']} | 单笔数量: {state['volume']}\n当前策略: {state['strategy_name']}\n启动时间: {state['start_time']}")
            self.btn_create.setEnabled(False)
            self.btn_change.setEnabled(True)
            self.btn_view.setEnabled(True)
            self.btn_end.setEnabled(True)
            self.start_engine()
        else:
            self.lbl_base.setText("当前无运行中的模拟交易")
            self.lbl_metrics.setText("收益率: -- | 夏普: -- | 回撤: --")
            self.table_logs.setRowCount(0)
            self.btn_create.setEnabled(True)
            self.btn_change.setEnabled(False)
            self.btn_view.setEnabled(False)
            self.btn_end.setEnabled(False)
            self.stop_engine()

    def start_engine(self):
        if self.engine is None or not self.engine.isRunning():
            from quant_system.services import SimTradeEngine
            self.engine = SimTradeEngine()
            self.engine.update_signal.connect(self.on_engine_update)
            self.engine.start()

    def stop_engine(self):
        if self.engine is not None:
            self.engine.stop()
            self.engine.wait()
            self.engine = None

    def on_engine_update(self, metrics, recommendations, log_msg):
        if metrics:
            self.lbl_metrics.setText(
                f"收益率: {metrics.get('total_return', 0):+.2f}% | "
                f"总盈亏: {metrics.get('total_profit', 0):.2f} | "
                f"夏普: {metrics.get('sharpe_ratio', 0):.2f}"
            )

        if log_msg:
            self.table_logs.insertRow(0)
            now = time.strftime("%H:%M:%S")
            self.table_logs.setItem(0, 0, QTableWidgetItem(now))
            self.table_logs.setItem(0, 1, QTableWidgetItem("系统监控"))
            self.table_logs.setItem(0, 2, QTableWidgetItem("--"))
            self.table_logs.setItem(0, 3, QTableWidgetItem(log_msg))

            if self.table_logs.rowCount() > 50:
                self.table_logs.removeRow(50)

    def _is_running(self):
        return StateManager.load_sim_state().get('is_running', False)
