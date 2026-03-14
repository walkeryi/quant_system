from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout,
                             QDateEdit, QPushButton, QLabel, QMessageBox)
from PyQt6.QtCore import QDate
from data_preprocessing import DataPreprocessor


class CalendarTab(QWidget):
    def __init__(self):
        super().__init__()
        self.dp = DataPreprocessor()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow("选择日期:", self.date_edit)

        self.check_btn = QPushButton("查询是否交易日")
        self.check_btn.clicked.connect(self.check)
        form.addRow(self.check_btn)

        self.result_label = QLabel("")
        self.result_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        form.addRow("结果:", self.result_label)

        layout.addLayout(form)
        layout.addStretch()

    def check(self):
        date = self.date_edit.date().toString("yyyy-MM-dd")
        try:
            is_trade = self.dp.is_trading_day(date)
            if is_trade is None:
                self.result_label.setText("查询失败")
                self.result_label.setStyleSheet("color: gray;")
            elif is_trade:
                self.result_label.setText("✅ 交易日")
                self.result_label.setStyleSheet("color: green;")
            else:
                self.result_label.setText("❌ 非交易日")
                self.result_label.setStyleSheet("color: red;")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查询异常：{e}")