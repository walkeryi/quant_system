# ui/widgets/stock_tab.py
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QMessageBox, QTabWidget, QGridLayout, QGroupBox, QDialog)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.charts.fenshi_chart_widget import FenshiChartWidget
from ui.charts.fenshi_volume_chart_widget import FenshiVolumeChartWidget
from ui.charts.kline_chart_widget import KlineChartWidget
from ui.threads.fenshi_thread import FenshiDataThread
from ui.threads.daily_thread import DailyDataThread
from ui.threads.weekly_thread import WeeklyDataThread
from ui.threads.monthly_thread import MonthlyDataThread
from ui.threads.trade_thread import TradeThread

# 引入会话信息和登录弹窗
from login import Session, LoginWindow

class StockTab(QWidget):
    switch_requested = pyqtSignal(int)

    def __init__(self, code, parent=None):
        super().__init__(parent)
        self.code = code
        self.base_info = {}
        self.fenshi_loaded = False
        self.kline_loaded = False

        self.cached_daily_df = None
        self.cached_weekly_df = None
        self.cached_monthly_df = None

        self.initUI()

    def update_trade_panel_title(self):
        """动态更新交易面板的标题"""
        if Session.is_logged_in:
            self.trade_group.setTitle(f"快捷交易 (已登录: {Session.username})")
        else:
            self.trade_group.setTitle("快捷交易 (未登录，点击交易即可登录)")

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # ========== 1. 顶部：数据与交易面板 ==========
        top_layout = QHBoxLayout()

        # --- 1.1 左侧：原有基础数据面板 ---
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

        # --- 1.2 右侧：全新交易面板 ---
        self.trade_group = QGroupBox()
        self.update_trade_panel_title() # 初始化标题
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

        # ========== 2. 图表面板 ==========
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

    # ================= 核心：发起实盘交易 =================
    def do_trade(self, endpoint, action_name):
        # 拦截：如果处于游客状态（未登录），则强制弹出登录框
        if not Session.is_logged_in:
            QMessageBox.information(self, "未登录", "您当前处于游客看盘模式，请先验证身份进行授权交易！")
            login_win = LoginWindow(self)
            if login_win.exec() != QDialog.DialogCode.Accepted:
                return  # 如果用户还是关闭了登录框，终止交易流程
            else:
                self.update_trade_panel_title()  # 登录成功，更新当前交易面板标题

                # 【新增】通知主窗口更新右上角的登录按钮状态
                top_window = self.window()
                if hasattr(top_window, 'update_login_btn_state'):
                    top_window.update_login_btn_state()

        price_str = self.trade_price.text().strip()
        hand_str = self.trade_hand.text().strip()
        policy = self.trade_policy.text().strip()

        if not price_str or not hand_str:
            QMessageBox.warning(self, "错误", "必须输入交易价格和手数！")
            return
        try:
            price = float(price_str)
            hand = int(hand_str)
        except ValueError:
            QMessageBox.warning(self, "错误", "价格必须是数字，手数必须是整数！")
            return

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
            QMessageBox.information(self, "下单成功",
                                    f"实盘订单已受理！\n单号：{res.get('orderid')}\n类型：{res.get('type')}")
        else:
            QMessageBox.critical(self, "下单失败", f"订单被拒绝\n错误码：{ret}\n原因：{msg}")

    # ================= 下方代码保持原样 =================
    def on_fenshi_crosshair_sync(self, x_idx):
        if x_idx == -1:
            self.fenshi_volume_widget.hide_crosshair()
        else:
            self.fenshi_volume_widget.sync_crosshair(x_idx)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'fenshi_price_widget'):
            self.fenshi_price_widget.apply_size()
            self.fenshi_volume_widget.set_width_stage(self.fenshi_price_widget.width_stage)
            if not self.fenshi_price_widget.height_is_custom:
                self.fenshi_price_widget.setFixedHeight(int(self.height() * 0.55))

    def on_fenshi_ready(self, df):
        import time, builtins
        if hasattr(builtins, 'JUMP_START_TIME') and builtins.JUMP_START_TIME is not None:
            fetch_cost = time.perf_counter() - builtins.JUMP_START_TIME
            print(
                f"[性能计时] {time.perf_counter() - builtins.APP_START_TIME:.4f}s | {self.code} 分时数据请求完成 (网络/解析耗时: {fetch_cost:.4f}s)，开始绘制图表...")

        render_start = time.perf_counter()

        # 隐藏加载提示文本
        if hasattr(self, 'loading_text'):
            self.loading_text.set_visible(False)

        self.fenshi_loaded = True
        base = df.attrs.get('base', {})
        self.base_info.update(base)
        self.update_data_panel(self.base_info)
        self.fenshi_price_widget.update_data(df, base)
        self.fenshi_volume_widget.update_data(df)

        if not self.trade_price.text():
            zuoshou = base.get('ZuoShou', 0)
            curr = df['price'].iloc[-1] if not df.empty else zuoshou
            self.trade_price.setText(f"{curr:.3f}")

        render_cost = time.perf_counter() - render_start
        print(
            f"[性能计时] {time.perf_counter() - builtins.APP_START_TIME:.4f}s | {self.code} 分时图表 UI 渲染完成 (独立绘图耗时: {render_cost:.4f}s)")

        # 计算双击跳转的总耗时
        if hasattr(builtins, 'JUMP_START_TIME') and builtins.JUMP_START_TIME is not None:
            total = time.perf_counter() - builtins.JUMP_START_TIME
            print(f"=======================================================")
            print(f"🚀 [性能计时] 股票 {self.code} 详情页跳转并渲染完毕！总耗时: {total:.4f} 秒")
            print(f"=======================================================\n")
            builtins.JUMP_START_TIME = None  # 归零，防止其他操作误触

    def update_data_panel(self, base):
        self.name_label.setText(base.get('name', '--'))
        self.labels['date'].setText(base.get('date', '--'))
        def fmt(key):
            val = base.get(key, 0)
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

    def on_tab_changed(self, index):
        if index == 0 and not self.fenshi_loaded:
            self.load_fenshi_data()
        elif index == 1 and not self.kline_loaded:
            self.load_kline_data()

    def on_kline_period_changed(self, period):
        if period == 'daily':
            if self.cached_daily_df is not None:
                self.kline_widget.update_data(self.cached_daily_df, 'daily')
            else:
                self.load_kline_data()
        elif period == 'weekly':
            if self.cached_weekly_df is not None:
                self.kline_widget.update_data(self.cached_weekly_df, 'weekly')
            else:
                self.load_weekly_data()
        elif period == 'monthly':
            if self.cached_monthly_df is not None:
                self.kline_widget.update_data(self.cached_monthly_df, 'monthly')
            else:
                self.load_monthly_data()

    def load_fenshi_data(self):
        # 1. 安全地添加加载提示
        if not hasattr(self, 'loading_text'):
            self.loading_text = self.fenshi_price_widget.chart.ax_price.text(
                0.5, 0.5, '数据拉取中，请稍候...',
                horizontalalignment='center', verticalalignment='center',
                transform=self.fenshi_price_widget.chart.ax_price.transAxes,
                color='#2196F3', fontsize=16, fontweight='bold', zorder=999
            )
        else:
            self.loading_text.set_text('数据拉取中，请稍候...')
            self.loading_text.set_color('#2196F3')
            self.loading_text.set_visible(True)

        self.fenshi_price_widget.chart.canvas.draw()

        # 2. 开启线程拉取数据
        self.thread = FenshiDataThread(self.code)
        self.thread.finished.connect(self.on_fenshi_ready)
        # 移除旧的弹窗信号，接入新的无弹窗错误处理
        if hasattr(self.thread, 'error'):
            self.thread.error.connect(self.on_data_load_failed)
        self.thread.start()

    def on_data_load_failed(self, error_msg):
        """【优化】退市及加载错误处理 - 不再弹窗，直接显示在图表上"""
        if hasattr(self, 'loading_text'):
            msg_text = "该股票已退市或代码无效" if "退市" in str(error_msg) or "302" in str(error_msg) or "DELISTED" in str(error_msg) else f"无数据/加载失败"
            self.loading_text.set_text(msg_text)
            self.loading_text.set_color('#f44336')  # 醒目红
            self.fenshi_price_widget.chart.canvas.draw()

    def on_kline_load_failed(self, error_msg, period_name):
        """【优化】K线退市及错误处理 - 不再弹窗，直接显示在K线图表上"""
        try:
            msg = "该股票已退市或代码无效" if "退市" in str(error_msg) or "302" in str(error_msg) or "DELISTED" in str(error_msg) else f"无{period_name}数据/加载失败"
            # 兼容获取 matplotlib axes 来绘制错误信息
            if hasattr(self.kline_widget, 'chart') and hasattr(self.kline_widget.chart, 'figure'):
                axes = self.kline_widget.chart.figure.axes
                if axes:
                    ax = axes[0]
                    ax.clear()
                    ax.text(0.5, 0.5, msg,
                            horizontalalignment='center', verticalalignment='center',
                            transform=ax.transAxes, color='#f44336', fontsize=16, fontweight='bold')
                    self.kline_widget.chart.canvas.draw()
        except Exception as e:
            print(f"K线图错误提示渲染异常: {e}")

    def load_kline_data(self):
        import time, builtins
        # 记录首次点击K线图的时间
        self.kline_fetch_start = time.perf_counter()
        print(
            f"\n[性能计时] {time.perf_counter() - builtins.APP_START_TIME:.4f}s | ---> 首次切换至 K线图，开始请求 {self.code} 日K数据...")

        self.kline_thread = DailyDataThread(self.code)
        self.kline_thread.finished.connect(self.on_daily_ready)
        # 接入无弹窗拦截
        self.kline_thread.error.connect(lambda e: self.on_kline_load_failed(e, "日线"))
        self.kline_thread.start()

    def on_daily_ready(self, df):
        import time, builtins
        fetch_cost = time.perf_counter() - getattr(self, 'kline_fetch_start', time.perf_counter())
        print(
            f"[性能计时] {time.perf_counter() - builtins.APP_START_TIME:.4f}s | {self.code} 日K数据请求完成 (网络/解析耗时: {fetch_cost:.4f}s)，开始绘制图表...")

        render_start = time.perf_counter()

        self.kline_loaded = True
        self.cached_daily_df = df
        if self.kline_widget.btn_daily.isChecked():
            self.kline_widget.update_data(df, 'daily')

        render_cost = time.perf_counter() - render_start
        print(
            f"[性能计时] {time.perf_counter() - builtins.APP_START_TIME:.4f}s | {self.code} 日K线图表 UI 渲染完成 (独立绘图耗时: {render_cost:.4f}s)")

        # 计算K线加载的总耗时
        if hasattr(self, 'kline_fetch_start'):
            total = time.perf_counter() - self.kline_fetch_start
            print(f"=======================================================")
            print(f"🚀 [性能计时] {self.code} K线图完整加载及渲染完毕！总耗时: {total:.4f} 秒")
            print(f"=======================================================\n")
            del self.kline_fetch_start

    def load_weekly_data(self):
        self.weekly_thread = WeeklyDataThread(self.code)
        self.weekly_thread.finished.connect(self.on_weekly_ready)
        self.weekly_thread.error.connect(lambda e: self.on_kline_load_failed(e, "周线"))
        self.weekly_thread.start()

    def on_weekly_ready(self, df):
        self.cached_weekly_df = df
        if self.kline_widget.btn_weekly.isChecked():
            self.kline_widget.update_data(df, 'weekly')

    def load_monthly_data(self):
        self.monthly_thread = MonthlyDataThread(self.code)
        self.monthly_thread.finished.connect(self.on_monthly_ready)
        self.monthly_thread.error.connect(lambda e: self.on_kline_load_failed(e, "月线"))
        self.monthly_thread.start()

    def on_monthly_ready(self, df):
        self.cached_monthly_df = df
        if self.kline_widget.btn_monthly.isChecked():
            self.kline_widget.update_data(df, 'monthly')
