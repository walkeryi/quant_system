import sys
from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QStatusBar, QMessageBox,
                             QLineEdit, QLabel, QWidget, QHBoxLayout, QVBoxLayout,
                             QSizePolicy, QPushButton, QDialog, QSizeGrip)
from PyQt6.QtGui import QAction, QCursor, QMouseEvent
from PyQt6.QtCore import Qt, QPoint

from ui.stock_list_tab import StockListTab
from ui.search_completer import SearchCompleter
from login import LoginWindow, Session


class CustomTitleBar(QWidget):
    """自定义现代化无边框标题栏"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedHeight(38)
        self.setStyleSheet("background-color: #202124; color: #ffffff;")

        self.start_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 0, 0)
        layout.setSpacing(15)

        # 1. Logo / 标题
        title_label = QLabel("量化交易系统")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #e8eaed;")
        layout.addWidget(title_label)

        layout.addStretch()

        # 2. 搜索框 (靠右)
        self.parent_window.search_completer = SearchCompleter(self.parent_window)
        self.parent_window.search_edit = self.parent_window.search_completer.setup_search_box(self)
        self.parent_window.search_completer.set_data_source(self.parent_window._get_search_results)
        self.parent_window.search_completer.item_selected.connect(self.parent_window.on_search_item_selected)
        layout.addWidget(self.parent_window.search_edit)

        # 3. 登录按钮 (靠右)
        self.login_btn = QPushButton()
        self.login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.login_btn.clicked.connect(self.parent_window.show_login_dialog)
        layout.addWidget(self.login_btn)

        # 4. 窗口控制按钮 (最小化、最大化、关闭，紧贴最右侧)
        btn_style = """
            QPushButton { background-color: transparent; border: none; font-size: 14px; color: #9aa0a6; }
            QPushButton:hover { background-color: #303134; color: white; }
        """
        close_btn_style = """
            QPushButton { background-color: transparent; border: none; font-size: 14px; color: #9aa0a6; }
            QPushButton:hover { background-color: #e81123; color: white; }
        """

        ctrl_layout = QHBoxLayout()
        ctrl_layout.setContentsMargins(10, 0, 0, 0)
        ctrl_layout.setSpacing(0)

        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(45, 38)
        self.min_btn.setStyleSheet(btn_style)
        self.min_btn.clicked.connect(self.parent_window.showMinimized)

        self.max_btn = QPushButton("☐")
        self.max_btn.setFixedSize(45, 38)
        self.max_btn.setStyleSheet(btn_style)
        self.max_btn.clicked.connect(self.toggle_max_restore)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(45, 38)
        self.close_btn.setStyleSheet(close_btn_style)
        self.close_btn.clicked.connect(self.parent_window.close)

        ctrl_layout.addWidget(self.min_btn)
        ctrl_layout.addWidget(self.max_btn)
        ctrl_layout.addWidget(self.close_btn)

        layout.addLayout(ctrl_layout)

    def toggle_max_restore(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self.max_btn.setText("☐")
        else:
            self.parent_window.showMaximized()
            self.max_btn.setText("❐")

    # ================= 实现拖拽移动窗口 =================
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.start_pos is not None:
            delta = event.globalPosition().toPoint() - self.start_pos
            self.parent_window.move(self.parent_window.pos() + delta)
            self.start_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.start_pos = None

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_max_restore()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("量化交易系统")
        self.setGeometry(100, 100, 1300, 800)

        # 【核心】隐藏操作系统自带的标题栏和边框
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        # === 懒加载组件占位符 ===
        self.daily_tab = None
        self.backtest_tab = None
        self.calendar_tab = None

        self.initUI()
        self.initStatusBar()
        self.update_login_btn_state()

    def initUI(self):
        # 建立一个全局容器来承载 自定义标题栏 和 主体内容
        wrapper = QWidget()
        self.setCentralWidget(wrapper)

        main_layout = QVBoxLayout(wrapper)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 顶部贴入我们自定义的标题栏
        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)

        # 2. 下方放入原本的选项卡
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # 首屏只加载“股票列表”，保证极速启动
        self.stock_list_tab = StockListTab()
        self.stock_list_tab.stock_double_clicked.connect(self.load_stock_daily)
        self.tabs.addTab(self.stock_list_tab, "股票数据")

        # 其它标签页只放置空的占位组件
        self.tabs.addTab(QWidget(), "个股详情")
        self.tabs.addTab(QWidget(), "量化回测")
        self.tabs.addTab(QWidget(), "交易日历")

        # 绑定点击切换事件，触发懒加载
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        print(f"\n[主窗口追踪] 捕获到 Tab 切换动作，目标索引: {index}")
        try:
            if index == 1 and self.daily_tab is None:
                from ui.daily_tab import DailyTab
                self.daily_tab = DailyTab()
                self.tabs.blockSignals(True)
                self.tabs.removeTab(1)
                self.tabs.insertTab(1, self.daily_tab, "个股详情")
                self.tabs.setCurrentIndex(1)
                self.tabs.blockSignals(False)

            elif index == 2 and self.backtest_tab is None:
                print("[主窗口追踪] ---> 开始懒加载【量化回测】模块 <---")

                print("[主窗口追踪] 步骤 1：尝试导入 ui.quant_backtest_tab 模块...")
                from ui.quant_backtest_tab import QuantBacktestTab

                print("[主窗口追踪] 步骤 2：导入成功！准备实例化 QuantBacktestTab...")
                self.backtest_tab = QuantBacktestTab()

                print("[主窗口追踪] 步骤 3：实例化完成！准备替换组件...")
                self.tabs.blockSignals(True)

                print("[主窗口追踪] 步骤 4：尝试移除旧的占位 Tab...")
                self.tabs.removeTab(2)

                print("[主窗口追踪] 步骤 5：尝试插入真正的回测 Tab...")
                self.tabs.insertTab(2, self.backtest_tab, "量化回测")

                print("[主窗口追踪] 步骤 6：尝试切换页面焦点...")
                self.tabs.setCurrentIndex(2)

                print("[主窗口追踪] 步骤 7：恢复系统信号...")
                self.tabs.blockSignals(False)

                print("[主窗口追踪] ---> 量化回测模块加载彻底完成！ <---")

            elif index == 3 and self.calendar_tab is None:
                from ui.calendar_tab import CalendarTab
                self.calendar_tab = CalendarTab()
                self.tabs.blockSignals(True)
                self.tabs.removeTab(3)
                self.tabs.insertTab(3, self.calendar_tab, "交易日历")
                self.tabs.setCurrentIndex(3)
                self.tabs.blockSignals(False)

        except Exception as e:
            print(f"\n[主窗口致命错误] 捕获到异常: {str(e)}")
            import traceback
            traceback.print_exc()
    def load_stock_daily(self, code):
        if self.daily_tab is None:
            self.on_tab_changed(1)
        else:
            self.tabs.setCurrentIndex(1)
        self.daily_tab.load_stock(code)

    def update_login_btn_state(self):
        """根据会话动态更新自定义标题栏上按钮的UI和文字"""
        if Session.is_logged_in:
            self.title_bar.login_btn.setText(f"{Session.username}")
            self.title_bar.login_btn.setStyleSheet("""
                QPushButton { background-color: transparent; color: #4CAF50; border: none; font-size: 14px; font-weight: bold; }
                QPushButton:hover { color: #81C784; }
            """)
            self.title_bar.login_btn.setToolTip("已登录 (点击可切换账号)")
        else:
            self.title_bar.login_btn.setText("登录")
            self.title_bar.login_btn.setStyleSheet("""
                QPushButton { background-color: transparent; color: #bbbbbb; border: none; font-size: 14px; font-weight: bold; }
                QPushButton:hover { color: #2196F3; }
            """)
            self.title_bar.login_btn.setToolTip("未登录，点击进行身份验证")

    def show_login_dialog(self):
        """弹出登录框并处理回调"""
        login_win = LoginWindow(self)
        if login_win.exec() == QDialog.DialogCode.Accepted:
            self.update_login_btn_state()

    def _get_search_results(self, keyword):
        df = self.stock_list_tab.all_df
        if df is None or not keyword: return []
        mask = (df['code'].astype(str).str.contains(keyword, case=False) |
                df['name'].str.contains(keyword, case=False))
        filtered = df[mask].head(10)
        results = []
        for _, row in filtered.iterrows():
            results.append((str(row['code']), str(row['name']), self.stock_list_tab._get_exchange(str(row['code']))))
        return results

    def on_search_item_selected(self, code):
        self.load_stock_daily(code)

    def initStatusBar(self):
        self.statusBar().showMessage("系统就绪")
        # 确保无边框窗口的右下角有拖拽调整大小的控件
        self.statusBar().setSizeGripEnabled(True)