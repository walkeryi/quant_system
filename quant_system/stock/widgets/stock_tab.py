# -*- coding: utf-8 -*-
"""
个股详情面板
"""
import logging
import pandas as pd
from datetime import datetime, time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QMessageBox, QTabWidget, QGridLayout, QGroupBox, QDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from quant_system.charts import FenshiChartWidget, FenshiVolumeChartWidget, KlineChartWidget
from quant_system.user import Session, LoginWindow
from quant_system.services import TraderAPI

logger = logging.getLogger('quant_system')


class StockTab(QWidget):
    switch_requested = pyqtSignal(int)
    price_updated = pyqtSignal(str, dict)

    def __init__(self, code, parent=None):
        super().__init__(parent)
        self.code = code
        self.base_info = {}
        self.fenshi_loaded = False
        self.kline_loaded = False
        self.is_background_refresh = False
        self.initUI()
        self.init_timer()

    def init_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.auto_refresh_data)
        self.refresh_timer.start(60000)

    def _update_refresh_timer_state(self):
        should_run = self.isVisible() and getattr(self, 'tab_widget', None) and self.tab_widget.currentIndex() == 0
        if should_run and not self.refresh_timer.isActive():
            self.refresh_timer.start(60000)
        elif not should_run and self.refresh_timer.isActive():
            self.refresh_timer.stop()

    def is_trading_time(self):
        now = datetime.now()
        if now.weekday() >= 5:
            return False
        curr = now.time()
        return (time(9, 15) <= curr <= time(11, 35)) or (time(13, 0) <= curr <= time(15, 10))

    def auto_refresh_data(self):
        if not self.isVisible():
            return
        if not self.is_trading_time():
            return
        if not getattr(self, 'tab_widget', None) or self.tab_widget.currentIndex() != 0:
            return
        if hasattr(self, 'thread') and self.thread.isRunning():
            return
        self.is_background_refresh = True
        self.load_fenshi_data()

    def update_trade_panel_title(self):
        if Session.is_logged_in:
            self.trade_group.setTitle(f"快捷交易 (已登录: {Session.username})")
        else:
            self.trade_group.setTitle("快捷交易 (未登录，点击交易即可登录)")

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        top_layout = QHBoxLayout()

        data_panel = QWidget()
        data_panel.setMaximumHeight(160)
        data_layout = QHBoxLayout(data_panel)
        data_layout.setContentsMargins(0, 0, 0, 0)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.code_label = QLabel(self.code)
        self.code_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.name_label = QLabel("--")
        self.name_label.setStyleSheet("font-size: 18px; color: gray;")
        left_layout.addWidget(self.code_label)
        left_layout.addWidget(self.name_label)
        left_layout.addStretch()

        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        self.prev_btn = QPushButton("◀")
        self.next_btn = QPushButton("▶")
        self.prev_btn.setFixedSize(40, 40)
        self.next_btn.setFixedSize(40, 40)
        self.prev_btn.clicked.connect(lambda: self.switch_requested.emit(-1))
        self.next_btn.clicked.connect(lambda: self.switch_requested.emit(1))
        btn_layout.addWidget(self.prev_btn)
        btn_layout.addWidget(self.next_btn)

        right_widget = QWidget()
        right_layout = QGridLayout(right_widget)
        self.labels = {}
        fields = [('date', '日期'), ('open', '开盘'), ('high', '最高'), ('low', '最低'), ('close', '昨收'),
                  ('振幅', '振幅(%)'), ('pe', '市盈率'), ('pb', '市净率'), ('mkt_cap', '市值(万)'), ('nwb', '内外比')]
        for i, (key, desc) in enumerate(fields):
            row, col = divmod(i, 2)
            right_layout.addWidget(QLabel(f"{desc}:"), row, col * 2)
            val_lbl = QLabel("--")
            val_lbl.setStyleSheet("font-weight: bold; color: #eee;")
            right_layout.addWidget(val_lbl, row, col * 2 + 1)
            self.labels[key] = val_lbl

        data_layout.addWidget(left_widget, 1)
        data_layout.addWidget(btn_widget, 0)
        data_layout.addWidget(right_widget, 2)
        top_layout.addWidget(data_panel, stretch=3)

        self.trade_group = QGroupBox()
        self.update_trade_panel_title()
        self.trade_group.setMaximumHeight(160)
        trade_layout = QGridLayout(self.trade_group)
        trade_layout.addWidget(QLabel("价格:"), 0, 0)
        self.trade_price = QLineEdit()
        self.trade_price.setPlaceholderText("限价/市价")
        trade_layout.addWidget(self.trade_price, 0, 1)
        trade_layout.addWidget(QLabel("手数:"), 1, 0)
        self.trade_hand = QLineEdit("1")
        trade_layout.addWidget(self.trade_hand, 1, 1)
        trade_layout.addWidget(QLabel("策略:"), 2, 0)
        self.trade_policy = QLineEdit("网格交易")
        trade_layout.addWidget(self.trade_policy, 2, 1)
        btn_buy_inst = QPushButton("即时买入")
        btn_sell_inst = QPushButton("即时卖出")
        btn_buy_limit = QPushButton("委托买入")
        btn_sell_limit = QPushButton("委托卖出")
        btn_buy_inst.setStyleSheet("background-color: #ef5350; color: white;")
        btn_sell_inst.setStyleSheet("background-color: #26a69a; color: white;")
        btn_buy_limit.setStyleSheet("background-color: #d32f2f; color: white;")
        btn_sell_limit.setStyleSheet("background-color: #00796b; color: white;")
        trade_layout.addWidget(btn_buy_inst, 0, 2)
        trade_layout.addWidget(btn_sell_inst, 0, 3)
        trade_layout.addWidget(btn_buy_limit, 1, 2)
        trade_layout.addWidget(btn_sell_limit, 1, 3)
        btn_buy_inst.clicked.connect(lambda: self.do_trade('ssjy_jimairu', '即时买入'))
        btn_sell_inst.clicked.connect(lambda: self.do_trade('ssjy_jimaichu', '即时卖出'))
        btn_buy_limit.clicked.connect(lambda: self.do_trade('ssjy_weimairu', '委托买入'))
        btn_sell_limit.clicked.connect(lambda: self.do_trade('ssjy_weimaichu', '委托卖出'))

        top_layout.addWidget(self.trade_group, stretch=2)
        main_layout.addLayout(top_layout)

        self.tab_widget = QTabWidget()
        fenshi_page = QWidget()
        fenshi_layout = QVBoxLayout(fenshi_page)
        fenshi_layout.setContentsMargins(0, 0, 0, 0)
        fenshi_layout.setSpacing(0)
        self.fenshi_price_widget = FenshiChartWidget()
        self.fenshi_volume_widget = FenshiVolumeChartWidget()
        self.fenshi_price_widget.widthStageChanged.connect(self.fenshi_volume_widget.set_width_stage)
        self.fenshi_price_widget.crosshairSyncSignal.connect(self.on_fenshi_crosshair_sync)
        fenshi_layout.addWidget(self.fenshi_price_widget, stretch=3)
        fenshi_layout.addWidget(self.fenshi_volume_widget, stretch=1)
        self.tab_widget.addTab(fenshi_page, "分时图")

        self.kline_widget = KlineChartWidget()
        self.kline_widget.period_changed.connect(self.on_kline_period_changed)
        self.tab_widget.addTab(self.kline_widget, "K线图")

        main_layout.addWidget(self.tab_widget)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def do_trade(self, endpoint, action_name):
        if not Session.is_logged_in:
            QMessageBox.information(self, "未登录", "您当前处于游客看盘模式，请先验证身份进行授权交易！")
            login_win = LoginWindow(self)
            if login_win.exec() != QDialog.DialogCode.Accepted:
                return
            self.update_trade_panel_title()
            top_window = self.window()
            if hasattr(top_window, 'update_login_btn_state'):
                top_window.update_login_btn_state()
        price_str = self.trade_price.text().strip()
        hand_str = self.trade_hand.text().strip()
        policy = self.trade_policy.text().strip()
        if not price_str or not hand_str:
            return QMessageBox.warning(self, "错误", "必须输入交易价格和手数！")
        try:
            price = float(price_str)
            hand = int(hand_str)
        except ValueError:
            return QMessageBox.warning(self, "错误", "价格必须是数字，手数必须是整数！")
        reply = QMessageBox.question(
            self, "确认下单",
            f"您确认对 {self.code} 执行 【{action_name}】 吗？\n\n价格：{price} 元\n数量：{hand} 手\n策略：{policy}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return
        self.trade_thread = TradeThread(endpoint, self.code, price, hand, policy)
        self.trade_thread.finished.connect(self.on_trade_result)
        self.trade_thread.start()

    def on_trade_result(self, res):
        ret = res.get('ret')
        msg = res.get('msg', '未知异常')
        if ret == 100:
            QMessageBox.information(self, "下单成功", f"实盘订单已受理！\n单号：{res.get('orderid')}")
        else:
            QMessageBox.critical(self, "下单失败", f"错误码：{ret}\n原因：{msg}")

    def on_fenshi_crosshair_sync(self, x_idx):
        if x_idx == -1:
            self.fenshi_volume_widget.hide_crosshair()
        else:
            self.fenshi_volume_widget.sync_crosshair(x_idx)

    def load_fenshi_data(self):
        if not hasattr(self, 'loading_text'):
            self.loading_text = self.fenshi_price_widget.chart.ax_price.text(
                0.5, 0.5, '数据拉取中...',
                ha='center', va='center',
                transform=self.fenshi_price_widget.chart.ax_price.transAxes,
                color='#2196F3', zorder=999
            )
        else:
            self.loading_text.set_visible(True)
        self.fenshi_price_widget.chart.canvas.draw()

        from ..threads.fenshi_thread import FenshiDataThread
        self.thread = FenshiDataThread(self.code)
        self.thread.finished.connect(self.on_fenshi_ready)
        if hasattr(self.thread, 'error'):
            self.thread.error.connect(self.on_data_load_failed)
        self.thread.start()

    def on_fenshi_ready(self, df):
        import time as ti, builtins
        logger.info(f"[Widget] code={self.code} on_fenshi_ready: type={type(df).__name__} "
                    f"is_empty={df.empty if hasattr(df, 'empty') else 'N/A'} "
                    f"cols={list(df.columns) if hasattr(df, 'columns') else 'N/A'}")
        if hasattr(self, 'loading_text'):
            self.loading_text.set_visible(False)
        self.fenshi_loaded = True

        base = df.attrs.get('base', {})
        self.base_info.update(base)
        self.update_data_panel(self.base_info)
        logger.info(f"[Widget] code={self.code} base_keys={list(base.keys())} zuoshou={base.get('ZuoShou', 'N/A')}")

        try:
            self.fenshi_price_widget.update_data(df, base)
            logger.info(f"[Widget] code={self.code} fenshi_price_widget.update_data 完成")
        except Exception as e:
            logger.exception(f"[Widget] code={self.code} fenshi_price_widget.update_data 异常: {e}")

        try:
            self.fenshi_volume_widget.update_data(df)
            logger.info(f"[Widget] code={self.code} fenshi_volume_widget.update_data 完成")
        except Exception as e:
            logger.exception(f"[Widget] code={self.code} fenshi_volume_widget.update_data 异常: {e}")

        if not df.empty and 'price' in df.columns:
            last = df.iloc[-1]
            snapshot = {
                'price': float(last['price']),
                'pct_chg': float(last.get('pct_chg', 0)),
                'high': float(base.get('ZuiGao', 0)) / 1000.0,
                'low': float(base.get('ZuiDi', 0)) / 1000.0,
                'volume': float(df['minute_volume'].sum()) if 'minute_volume' in df.columns and not df['minute_volume'].isna().all() else 0.0
            }
            self.price_updated.emit(self.code, snapshot)

        if not self.is_background_refresh and not self.trade_price.text():
            zuoshou = float(base.get('ZuoShou', 0)) / 1000.0
            curr = df['price'].iloc[-1] if not df.empty and 'price' in df.columns else zuoshou
            self.trade_price.setText(f"{curr:.3f}")

        self.is_background_refresh = False

    def update_data_panel(self, base):
        self.name_label.setText(base.get('name', '--'))
        self.labels['date'].setText(base.get('date', '--'))

        def fmt(key):
            val = base.get(key, 0)
            if key in ['KaiPan', 'ZuiGao', 'ZuiDi', 'ZuoShou']:
                return f"{float(val) / 1000.0:.2f}" if val else "--"
            return f"{float(val):.2f}" if val else "--"

        self.labels['open'].setText(fmt('KaiPan'))
        self.labels['high'].setText(fmt('ZuiGao'))
        self.labels['low'].setText(fmt('ZuiDi'))
        self.labels['close'].setText(fmt('ZuoShou'))
        self.labels['振幅'].setText(f"{base.get('ZhenFu', '--')}%")
        self.labels['pe'].setText(fmt('ShiYingLv'))
        self.labels['pb'].setText(fmt('ShiJingLv'))
        self.labels['mkt_cap'].setText(f"{base.get('ShiZhi', 0):,.0f}")
        self.labels['nwb'].setText(fmt('NeiWaiBi'))

    def on_data_load_failed(self, error_msg):
        logger.warning(f"[Widget] code={self.code} 数据加载失败: {error_msg}")
        if hasattr(self, 'loading_text'):
            self.loading_text.set_text(f"数据拉取失败: {error_msg}")
            self.loading_text.set_color('#f44336')
            self.fenshi_price_widget.chart.canvas.draw()

    def on_kline_load_failed(self, error_msg, period_name):
        try:
            if hasattr(self.kline_widget, 'chart') and hasattr(self.kline_widget.chart, 'figure'):
                axes = self.kline_widget.chart.figure.axes
                if axes:
                    ax = axes[0]
                    ax.clear()
                    ax.text(0.5, 0.5, f"无{period_name}数据", ha='center', va='center',
                            transform=ax.transAxes, color='#f44336')
                    self.kline_widget.chart.canvas.draw()
        except Exception:
            pass

    def load_kline_data(self):
        from ..threads.daily_thread import DailyDataThread
        self.kline_thread = DailyDataThread(self.code)
        self.kline_thread.finished.connect(self.on_daily_ready)
        self.kline_thread.error.connect(lambda e: self.on_kline_load_failed(e, "日线"))
        self.kline_thread.start()

    def on_daily_ready(self, df):
        self.kline_loaded = True
        if self.kline_widget.btn_daily.isChecked():
            self.kline_widget.update_data(df, 'daily')

    def load_weekly_data(self):
        from ..threads.weekly_thread import WeeklyDataThread
        self.weekly_thread = WeeklyDataThread(self.code)
        self.weekly_thread.finished.connect(lambda df: self.kline_widget.update_data(df, 'weekly'))
        self.weekly_thread.start()

    def load_monthly_data(self):
        from ..threads.monthly_thread import MonthlyDataThread
        self.monthly_thread = MonthlyDataThread(self.code)
        self.monthly_thread.finished.connect(lambda df: self.kline_widget.update_data(df, 'monthly'))
        self.monthly_thread.start()

    def on_tab_changed(self, index):
        self._update_refresh_timer_state()
        if index == 0 and not self.fenshi_loaded:
            self.load_fenshi_data()
        elif index == 1 and not self.kline_loaded:
            self.load_kline_data()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_refresh_timer_state()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._update_refresh_timer_state()

    def on_kline_period_changed(self, period):
        if period == 'daily':
            self.load_kline_data()
        elif period == 'weekly':
            self.load_weekly_data()
        elif period == 'monthly':
            self.load_monthly_data()


class TradeThread:
    """交易线程（简化版）"""
    def __init__(self, endpoint, code, price, hand, policy):
        self.endpoint = endpoint
        self.code = code
        self.price = price
        self.hand = hand
        self.policy = policy
        self.finished = pyqtSignal(dict) if 'PyQt6' else None

    def start(self):
        from PyQt6.QtCore import QThread, pyqtSignal
        class _T(QThread):
            done = pyqtSignal(dict)
            def __init__(t, ep, code, price, hand, policy):
                super().__init__()
                t.ep, t.code, t.price, t.hand, t.policy = ep, code, price, hand, policy
            def run(t):
                res = TraderAPI.execute(t.ep, t.code, t.price, t.hand, t.policy)
                t.done.emit(res)
        self._t = _T(self.endpoint, self.code, self.price, self.hand, self.policy)
        self._t.done.connect(self.finished.emit)
        self._t.start()
