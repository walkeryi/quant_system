# -*- coding: utf-8 -*-
"""
聊天模块的 UI 组件
"""
from __future__ import annotations
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QLineEdit, QPushButton, QApplication)
from PyQt6.QtCore import pyqtSignal
from typing import Optional

from ..user import Session
from .client import ChatClient, MockChatClient
from .models import ChatMessage, MessageType


class ChatTab(QWidget):
    """消息中心：即时通信与分享展示模块"""

    prepare_share_requested = pyqtSignal()

    def __init__(self, use_mock: bool = True):
        super().__init__()
        self.use_mock = use_mock
        self.chat_client = None
        self.initUI()
        self.initClient()

    def initUI(self):
        layout = QVBoxLayout(self)

        self.chat_display = QTextBrowser()
        self.chat_display.setStyleSheet("""
            background-color: #1e1e1e;
            color: #d4d4d4;
            font-size: 14px;
            border: 1px solid #333;
        """)
        layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("输入消息或在此发送分享链接...")
        self.input_box.setStyleSheet("padding: 8px; background-color: #2c2c2c; color: white; border-radius: 4px;")
        self.input_box.returnPressed.connect(self.send_message)

        self.btn_send = QPushButton("发送")
        self.btn_send.setStyleSheet("""
            background-color: #2196F3;
            color: white;
            font-weight: bold;
            padding: 8px 25px;
            border-radius: 4px;
        """)
        self.btn_send.clicked.connect(self.send_message)

        input_layout.addWidget(self.input_box)
        input_layout.addWidget(self.btn_send)
        layout.addLayout(input_layout)

        self.chat_display.append("<i style='color:#888;'>系统提示：欢迎进入量化交易聊天室。</i>")

    def initClient(self):
        if self.use_mock:
            self.chat_client = MockChatClient()
            self.chat_client.message_received.connect(self._display_message)
            self.chat_client.connect()
        else:
            self.chat_client = None
            self.chat_display.append("<i style='color:#ff9800;'>系统提示：当前为离线模式，消息仅本地显示。</i>")

    def send_message(self):
        text = self.input_box.text().strip()
        if not text:
            return

        username = Session.username if Session.username else "游客"

        if self.chat_client:
            self.chat_client.send_message(text, username)

        self.input_box.clear()

    def _display_message(self, message):
        html = message.to_html()
        self.chat_display.append(html)

    def prepare_shared_link(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if "http://quant_system/share" in text:
            self.input_box.setText(text)
            self.input_box.setFocus()

    def closeEvent(self, event):
        if self.chat_client:
            self.chat_client.disconnect()
        super().closeEvent(event)
