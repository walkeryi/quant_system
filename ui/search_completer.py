from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFontMetrics, QColor, QBrush


class SearchPopup(QWidget):
    item_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        fm = QFontMetrics(self.font())
        self.fixed_width = fm.horizontalAdvance("0" * 25) + 40
        self.setFixedWidth(self.fixed_width)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["代码", "名称", "市场"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(False)
        self.table.setMaximumHeight(300)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)  # 显示时不激活
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 自身不获取焦点
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 表格不获取焦点

        # 修正后的样式表（高对比）
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2D2D2D;          /* 深灰背景 */
                border: 1px solid #3E3E3E;           /* 深色边框 */
                font-size: 13px;
                gridline-color: #3E3E3E;             /* 网格线颜色与边框一致 */
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #3E3E3E;    /* 行分隔线 */
                color: #E0E0E0;                       /* 文字浅灰 */
            }
            QTableWidget::item:selected {
                background-color: #4A90D9;             /* 选中蓝色（保持不变） */
                color: white;
            }
            QTableWidget::item:hover {
                background-color: #3E3E3E;             /* 悬停时稍亮一点 */
            }
            QHeaderView::section {
                background-color: #1E1E1E;             /* 表头更深的黑色 */
                padding: 6px;
                border: none;
                border-bottom: 2px solid #4A90D9;      /* 表头底部蓝色线条，增加现代感 */
                font-weight: bold;
                color: #FFFFFF;                          /* 表头文字白色 */
            }
        """)

        layout.addWidget(self.table)
        self.table.cellClicked.connect(self._on_item_clicked)

    def set_data(self, data):
        self.table.setRowCount(len(data))
        for row, (code, name, exchange) in enumerate(data):
            code_item = QTableWidgetItem(code)
            name_item = QTableWidgetItem(name)
            exch_item = QTableWidgetItem(exchange)

            if row == 0:
                color = QColor("#FFD700")
                code_item.setForeground(QBrush(color))
                name_item.setForeground(QBrush(color))
                exch_item.setForeground(QBrush(color))
                font = code_item.font()
                font.setBold(True)
                code_item.setFont(font)
                name_item.setFont(font)
                exch_item.setFont(font)

            self.table.setItem(row, 0, code_item)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, exch_item)

        # 自适应高度
        if self.table.rowCount() > 0:
            row_height = self.table.rowHeight(0)
            header_height = self.table.horizontalHeader().height()
            total_height = header_height + row_height * len(data) + 4
            self.table.setFixedHeight(min(total_height, 300))
            self.setFixedHeight(self.table.height() + 2)

    def _on_item_clicked(self, row, column):
        code_item = self.table.item(row, 0)
        if code_item:
            self.item_selected.emit(code_item.text())
            self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Down:
            current = self.table.currentRow()
            if current < self.table.rowCount() - 1:
                self.table.setCurrentCell(current + 1, 0)
        elif event.key() == Qt.Key.Key_Up:
            current = self.table.currentRow()
            if current > 0:
                self.table.setCurrentCell(current - 1, 0)
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            current = self.table.currentRow()
            if current >= 0:
                self._on_item_clicked(current, 0)
        elif event.key() == Qt.Key.Key_Escape:
            self.hide()
        # 其他键不处理，也不调用 super()


class SearchCompleter(QWidget):
    item_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.popup = SearchPopup(parent)
        self.popup.item_selected.connect(self._on_item_selected)
        self.search_box = None
        self._data_source = None

    def setup_search_box(self, parent_widget):
        self.search_box = QLineEdit(parent_widget)
        self.search_box.setPlaceholderText("搜索股票...")
        self.search_box.setFixedSize(250, 32)  # 调宽一点
        self.search_box.textChanged.connect(self._on_search_text_changed)
        self.search_box.installEventFilter(self)
        return self.search_box

    def set_data_source(self, callback):
        self._data_source = callback

    def eventFilter(self, obj, event):
        if obj == self.search_box and event.type() == event.Type.KeyPress:
            if self.popup.isVisible():
                self.popup.keyPressEvent(event)
                # 返回 False 让事件继续传递给输入框
                return False
        return super().eventFilter(obj, event)

    def _on_search_text_changed(self, text):
        if not text.strip():
            self.popup.hide()
            return

        if self._data_source:
            data = self._data_source(text.strip().lower())
            if data:
                self.popup.set_data(data)
                pos = self.search_box.mapToGlobal(self.search_box.rect().bottomLeft())
                self.popup.move(pos.x(), pos.y() + 4)
                self.popup.show()
                # 强制焦点回到输入框
                QTimer.singleShot(10, self.search_box.setFocus)
            else:
                self.popup.hide()

    def _on_item_selected(self, code):
        self.search_box.clear()
        self.popup.hide()
        self.item_selected.emit(code)

    def hide_popup(self):
        self.popup.hide()