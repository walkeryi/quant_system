# -*- coding: utf-8 -*-
"""
交易日历 Tab - 优化版
- 月历视图，高亮交易日/休市日
- 支持预加载全年数据（并发请求 + 进度条）
- 添加图例说明
- 使用 QThread 规范多线程
- 预留节假日名称显示
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCalendarWidget, QTextEdit,
    QProgressBar, QComboBox, QFrame,
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QThread, QMutex, QTimer
from PyQt6.QtGui import QColor, QTextCharFormat, QPalette, QBrush, QEnterEvent, QFont

from quant_system.services.calendar_service import CalendarService


class PrefetchThread(QThread):
    """预加载线程 - 使用 QThread 规范"""
    progress = pyqtSignal(int, int, str)  # current, total, date_str
    finished = pyqtSignal(bool)  # success

    def __init__(self, service: CalendarService, year: int, max_workers: int = 10):
        super().__init__()
        self.service = service
        self.year = year
        self.max_workers = max_workers

    def run(self):
        success = self.service.prefetch_year(
            self.year,
            max_workers=self.max_workers,
            progress_callback=lambda current, total, date_str: self.progress.emit(current, total, date_str)
        )
        self.finished.emit(success)


class CalendarTab(QWidget):
    """交易日历 Tab - 优化版"""

    def __init__(self):
        super().__init__()
        self.calendar_service = CalendarService()
        self.year_cache: dict[int, dict[str, bool]] = {}
        self.current_year = QDate.currentDate().year()
        self.current_month = QDate.currentDate().month()
        self._pending_date = None
        self._prefetch_thread: PrefetchThread | None = None
        self._holiday_cache: dict[str, str] = {}  # 节假日名称缓存

        # 加载节假日数据
        self._load_holiday_names()

        self.initUI()
        self._apply_month_styles()
        self._load_current_month()

    def _load_holiday_names(self):
        """加载节假日名称数据"""
        # 这里可以连接外部节假日数据源
        # 目前使用静态数据
        self._holiday_cache = {
            '2024-01-01': '元旦',
            '2024-02-10': '春节',
            '2024-02-11': '春节',
            '2024-02-12': '春节',
            '2024-02-13': '春节',
            '2024-02-14': '春节',
            '2024-02-15': '春节',
            '2024-02-16': '春节',
            '2024-04-04': '清明节',
            '2024-04-05': '清明节',
            '2024-04-06': '清明节',
            '2024-05-01': '劳动节',
            '2024-05-02': '劳动节',
            '2024-05-03': '劳动节',
            '2024-05-04': '劳动节',
            '2024-05-05': '劳动节',
            '2024-06-10': '端午节',
            '2024-09-15': '中秋节',
            '2024-09-16': '中秋节',
            '2024-09-17': '中秋节',
            '2024-10-01': '国庆节',
            '2024-10-02': '国庆节',
            '2024-10-03': '国庆节',
            '2024-10-04': '国庆节',
            '2024-10-05': '国庆节',
            '2024-10-06': '国庆节',
            '2024-10-07': '国庆节',
            # 2025年节假日
            '2025-01-01': '元旦',
            '2025-01-28': '春节',
            '2025-01-29': '春节',
            '2025-01-30': '春节',
            '2025-01-31': '春节',
            '2025-02-01': '春节',
            '2025-02-02': '春节',
            '2025-02-03': '春节',
            '2025-02-04': '春节',
            '2025-04-04': '清明节',
            '2025-04-05': '清明节',
            '2025-04-06': '清明节',
            '2025-05-01': '劳动节',
            '2025-05-02': '劳动节',
            '2025-05-03': '劳动节',
            '2025-05-04': '劳动节',
            '2025-05-05': '劳动节',
            '2025-05-31': '端午节',
            '2025-10-01': '国庆节',
            '2025-10-02': '国庆节',
            '2025-10-03': '国庆节',
            '2025-10-04': '国庆节',
            '2025-10-05': '国庆节',
            '2025-10-06': '国庆节',
            '2025-10-07': '国庆节',
            '2025-10-08': '国庆节',
            # 2026年节假日 (部分)
            '2026-01-01': '元旦',
            '2026-02-17': '春节',
            '2026-02-18': '春节',
            '2026-02-19': '春节',
            '2026-02-20': '春节',
            '2026-02-21': '春节',
            '2026-02-22': '春节',
            '2026-02-23': '春节',
            '2026-02-24': '春节',
            '2026-04-04': '清明节',
            '2026-04-05': '清明节',
            '2026-04-06': '清明节',
            '2026-05-01': '劳动节',
            '2026-05-02': '劳动节',
            '2026-05-03': '劳动节',
            '2026-10-01': '国庆节',
            '2026-10-02': '国庆节',
            '2026-10-03': '国庆节',
            '2026-10-04': '国庆节',
            '2026-10-05': '国庆节',
            '2026-10-06': '国庆节',
            '2026-10-07': '国庆节',
            '2026-10-08': '国庆节',
        }

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ===== 工具栏 =====
        toolbar = QHBoxLayout()

        # 市场选择
        market_label = QLabel("市场:")
        market_label.setStyleSheet("color: #d4d4d4; font-weight: bold;")
        self.market_combo = QComboBox()
        self.market_combo.addItems(['A股 (沪深)', '港股 (HK)', '美股 (US)'])
        self.market_combo.setFixedWidth(120)
        self.market_combo.setStyleSheet(self._combo_style())
        self.market_combo.currentIndexChanged.connect(self._on_market_changed)

        # 预加载按钮
        self.prefetch_btn = QPushButton("预加载本年日历")
        self.prefetch_btn.setStyleSheet(self._btn_style())
        self.prefetch_btn.clicked.connect(self._prefetch_year)
        self.prefetch_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        toolbar.addWidget(market_label)
        toolbar.addWidget(self.market_combo)
        toolbar.addSpacing(20)
        toolbar.addWidget(self.prefetch_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # ===== 进度条 =====
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
                background-color: #252526;
                color: #d4d4d4;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        layout.addLayout(progress_layout)

        # ===== 当前月份指示器 =====
        self.month_indicator = QFrame()
        self.month_indicator.setStyleSheet("""
            QFrame {
                background-color: #1a4b77;
                border: 2px solid #2196F3;
                border-radius: 8px;
                padding: 8px 16px;
            }
        """)
        indicator_layout = QHBoxLayout(self.month_indicator)
        indicator_layout.setContentsMargins(10, 5, 10, 5)

        self.month_label = QLabel()
        self.month_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
            }
        """)

        self.back_to_today_btn = QPushButton("回到本月")
        self.back_to_today_btn.setFixedWidth(90)
        self.back_to_today_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 12px;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.back_to_today_btn.clicked.connect(self._go_to_today)

        indicator_layout.addWidget(self.month_label)
        indicator_layout.addStretch()
        indicator_layout.addWidget(self.back_to_today_btn)
        layout.addWidget(self.month_indicator)

        # ===== 日历组件 =====
        self.calendar = QCalendarWidget()
        self.calendar.setNavigationBarVisible(True)
        # 隐藏最左侧的周数列（去除干扰列）
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setFixedHeight(400)
        self.calendar.clicked.connect(self._on_date_clicked)
        self.calendar.currentPageChanged.connect(self._on_page_changed)

        self._style_calendar()
        layout.addWidget(self.calendar)

        # ===== 底部信息区 =====
        self.info_label = QTextEdit()
        self.info_label.setReadOnly(True)
        self.info_label.setFixedHeight(100)
        self.info_label.setStyleSheet(self._info_style())
        # 禁用文本交互，避免光标进入
        self.info_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(self.info_label)

        # 初始化今日信息
        today = QDate.currentDate()
        self._update_info(today.toString(Qt.DateFormat.ISODate), today)
        self._update_month_indicator()

    def _update_month_indicator(self):
        """更新月份指示器"""
        shown_year = self.calendar.yearShown()
        shown_month = self.calendar.monthShown()
        current_year = QDate.currentDate().year()
        current_month = QDate.currentDate().month()

        if shown_year == current_year and shown_month == current_month:
            # 当前月
            self.month_indicator.setStyleSheet("""
                QFrame {
                    background-color: #1a4b77;
                    border: 2px solid #2196F3;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
            """)
            self.month_label.setText(f"📅 当前月份: {shown_year}年 {shown_month}月")
            self.month_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
            self.back_to_today_btn.setEnabled(False)
        else:
            # 非当前月
            self.month_indicator.setStyleSheet("""
                QFrame {
                    background-color: #3d2a2a;
                    border: 2px solid #ff6b6b;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
            """)
            self.month_label.setText(f"📅 查看中: {shown_year}年 {shown_month}月")
            self.month_label.setStyleSheet("color: #ff6b6b; font-size: 16px; font-weight: bold;")
            self.back_to_today_btn.setEnabled(True)

    def _go_to_today(self):
        """回到本月"""
        today = QDate.currentDate()
        self.calendar.setSelectedDate(today)
        self.calendar.setCurrentPage(today.year(), today.month())
        self._update_month_indicator()
        self._update_info(today.toString(Qt.DateFormat.ISODate), today)
        self._apply_month_styles()

    def _combo_style(self):
        return """
            QComboBox {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QComboBox:hover {
                border: 1px solid #2196F3;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #888;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #444;
                selection-background-color: #1a4b77;
            }
        """

    def _style_calendar(self):
        self.calendar.setStyleSheet("""
            QCalendarWidget QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            QCalendarWidget QToolButton {
                background-color: #252526;
                color: #e8eaed;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: bold;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #333333;
            }
            QCalendarWidget QMenu {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #333;
            }
            QCalendarWidget QSpinBox {
                background-color: #252526;
                color: #e8eaed;
                border: 1px solid #333;
            }
            QCalendarWidget QSpinBox::up-button,
            QCalendarWidget QSpinBox::down-button {
                background-color: #333;
            }
            QCalendarWidget QAbstractItemView {
                background-color: #1e1e1e;
                color: #d4d4d4;
                selection-background-color: #1a4b77;
                border: 1px solid #333;
            }
            QCalendarWidget QAbstractItemView::item {
                padding: 4px;
                border-radius: 2px;
            }
            QCalendarWidget QAbstractItemView::item:hover {
                background-color: #2a2a2a;
            }
        """)

    def _btn_style(self):
        return """
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 7px 20px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """

    def _info_style(self):
        return """
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
        """

    def _apply_month_styles(self):
        """应用极简样式：本月1号红色，当月纯白，非当月灰色半透明"""
        year = self.calendar.yearShown()
        month = self.calendar.monthShown()

        first_of_month = QDate(year, month, 1)
        last_of_month = QDate(year, month, 1).addDays(-1).addMonths(1).addDays(-1)

        first_weekday = first_of_month.dayOfWeek()
        start_display = first_of_month.addDays(-(first_weekday - 1))
        last_weekday = last_of_month.dayOfWeek()
        end_display = last_of_month.addDays(7 - last_weekday)

        current = start_display
        while current <= end_display:
            qdate = current
            fmt = QTextCharFormat()

            # 清除背景色以及可能残留的其他格式（删除线、加粗等）
            fmt.clearBackground()
            fmt.setFontStrikeOut(False)
            fmt.setFontUnderline(False)
            fmt.setFontWeight(QFont.Weight.Normal)

            is_current_month = (qdate.month() == month)

            if is_current_month:
                if qdate.day() == 1:
                    # 本月的1号是红色 (使用偏柔和的红色在暗色背景下更舒适)
                    color = QColor("#ff5555")
                    fmt.setFontWeight(QFont.Weight.Bold)  # 稍微加粗一点点让1号更醒目
                else:
                    # 当月号码是纯白
                    color = QColor("#ffffff")
            else:
                # 非当月是灰色且透明度为50% (255 * 0.5 ≈ 127)
                color = QColor("#888888")
                color.setAlpha(127)

            fmt.setForeground(QBrush(color))
            self.calendar.setDateTextFormat(qdate, fmt)
            current = current.addDays(1)

    def _load_current_month(self):
        year = self.calendar.yearShown()
        month = self.calendar.monthShown()
        self._ensure_year_loaded(year)
        self._apply_month_styles()

    def _ensure_year_loaded(self, year: int):
        if year not in self.year_cache:
            self.year_cache[year] = {}
            self._load_year_from_cache(year)

    def _load_year_from_cache(self, year: int):
        """从本地缓存加载年份数据 - 优化版"""
        cache = self.year_cache[year]
        try:
            import pandas as pd
            from quant_system.config import TRADE_CALENDAR_CACHE
            import os
            if os.path.exists(TRADE_CALENDAR_CACHE):
                df = pd.read_csv(TRADE_CALENDAR_CACHE)
                if 'date' in df.columns and 'trade' in df.columns:
                    df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
                    year_df = df[df['date'].dt.year == year]
                    # 优化：使用 dict + zip 替代 iterrows
                    if not year_df.empty:
                        date_strs = year_df['date'].dt.strftime('%Y-%m-%d')
                        trades = year_df['trade'].astype(bool)
                        cache.update(dict(zip(date_strs, trades)))
        except Exception:
            pass

    def _is_trading_day(self, date_str: str) -> bool | None:
        """检查是否为交易日"""
        year = int(date_str[:4])
        if year in self.year_cache and date_str in self.year_cache[year]:
            return self.year_cache[year][date_str]
        return self.calendar_service.is_trading_day(date_str)

    def _update_info(self, date_str: str, qdate: QDate):
        """更新底部信息显示"""
        result = self._is_trading_day(date_str)
        day_names = ['一', '二', '三', '四', '五', '六', '日']
        weekday = qdate.dayOfWeek()
        weekday_name = day_names[weekday - 1]

        # 判断状态
        holiday_name = self._holiday_cache.get(date_str)
        is_weekend = weekday >= 6

        if result is True:
            if holiday_name:
                status = f'<span style="color:#4caf50; font-weight:bold;">是交易日</span> <span style="color:#ff6b6b;">(节假日调休)</span>'
            else:
                status = '<span style="color:#4caf50; font-weight:bold;">是交易日</span>'
        elif result is False:
            if holiday_name:
                status = f'<span style="color:#ff6b6b; font-weight:bold;">非交易日</span> <span style="color:#ff9800;">({holiday_name})</span>'
            elif is_weekend:
                status = '<span style="color:#888888; font-weight:bold;">非交易日</span> <span style="color:#666;">(周末)</span>'
            else:
                status = '<span style="color:#888888; font-weight:bold;">非交易日</span> <span style="color:#666;">(其他节假日)</span>'
        else:
            status = '<span style="color:#ff9800;">查询中...</span>'

        month_name = qdate.toString("M月")
        day_num = str(qdate.day())

        html = (
            f'<b>{qdate.year()}年 {month_name}{day_num}日 ({weekday_name}曜日)</b><br>'
            f'状态：{status}<br>'
            f'<span style="color:#666;">交易日 = 正常开市 &nbsp;|&nbsp; '
            f'休市 = 周末/节假日 | 节假日名称显示为红色</span>'
        )
        self.info_label.setHtml(html)

    def _on_date_clicked(self, qdate: QDate):
        date_str = qdate.toString(Qt.DateFormat.ISODate)
        year = qdate.year()
        if year not in self.year_cache:
            self._ensure_year_loaded(year)
        self._update_info(date_str, qdate)
        self._apply_month_styles()

    def _on_page_changed(self, year: int, month: int):
        self._ensure_year_loaded(year)
        self._apply_month_styles()
        self._update_month_indicator()

    def _on_market_changed(self, index: int):
        """切换市场"""
        market_codes = ['A', 'HK', 'US']
        market = market_codes[index]
        self.calendar_service = CalendarService(market=market)
        # 清空缓存，重新加载
        self.year_cache.clear()
        self._load_current_month()

    def _prefetch_year(self):
        """开始预加载年份数据"""
        year = QDate.currentDate().year()
        self.prefetch_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(365)
        self.progress_bar.setFormat(f"准备预加载 {year} 年...")

        # 使用 QThread 进行后台加载
        self._prefetch_thread = PrefetchThread(self.calendar_service, year)
        self._prefetch_thread.progress.connect(self._on_prefetch_progress)
        self._prefetch_thread.finished.connect(self._on_prefetch_done)
        self._prefetch_thread.start()

    def _on_prefetch_progress(self, current: int, total: int, date_str: str):
        """更新预加载进度"""
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"正在加载: {current}/{total} ({date_str})")

    def _on_prefetch_done(self, success: bool):
        """预加载完成"""
        year = QDate.currentDate().year()
        self.progress_bar.setVisible(False)
        self.prefetch_btn.setEnabled(True)

        if success:
            # 刷新缓存
            self.year_cache.pop(year, None)
            self._ensure_year_loaded(year)
            self._apply_month_styles()

            # 显示成功消息
            self._show_temp_message(f"{year} 年日历加载完成！", is_success=True)
        else:
            self._show_temp_message(f"{year} 年日历加载失败", is_success=False)

    def _show_temp_message(self, message: str, is_success: bool = True):
        """显示临时消息"""
        color = "#4caf50" if is_success else "#f44336"
        self.progress_bar.setVisible(True)
        self.progress_bar.setFormat(message)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
                background-color: #252526;
                color: {color};
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
        QTimer.singleShot(3000, self._hide_progress_bar)

    def _hide_progress_bar(self):
        """隐藏进度条"""
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
                background-color: #252526;
                color: #d4d4d4;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
            }
        """)

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        if self._prefetch_thread and self._prefetch_thread.isRunning():
            self._prefetch_thread.quit()
            self._prefetch_thread.wait()
        event.accept()
