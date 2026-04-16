# 文件路径: quant_system/ui/chat_tab.py
import time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, 
                             QLineEdit, QPushButton, QApplication)
from login import Session

class ChatTab(QWidget):
    """消息中心：即时通信与分享展示模块"""
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 1. 聊天室显示区域（展示即时聊天及分享链接）
        self.chat_display = QTextBrowser()
        self.chat_display.setStyleSheet("""
            background-color: #1e1e1e; 
            color: #d4d4d4; 
            font-size: 14px; 
            border: 1px solid #333;
        """)
        layout.addWidget(self.chat_display)
        
        # 2. 输入与发送区域
        input_layout = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("输入消息或在此发送分享链接...")
        self.input_box.setStyleSheet("padding: 8px; background-color: #2c2c2c; color: white; border-radius: 4px;")
        self.input_box.returnPressed.connect(self.send_message) # 支持回车发送
        
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
        
        # 初始欢迎语
        self.chat_display.append("<i style='color:#888;'>系统提示：欢迎进入量化交易聊天室。</i>")

    def send_message(self):
        """发送即时聊天信息"""
        text = self.input_box.text().strip()
        if not text:
            return
            
        username = Session.username if Session.username else "游客"
        timestamp = time.strftime("%H:%M:%S")
        
        # 需求要求：识别分享链接并进行差异化显示
        is_share = "http://quant_system/share" in text
        color = "#00e676" if is_share else "#2196F3" # 分享链接绿色，普通聊天蓝色
        
        prefix = "📢 [策略分享] " if "/strategy" in text else ("📊 [报告分享] " if "/report" in text else "")
        message_html = f"<b style='color:{color};'>[{timestamp}] {username}:</b> {prefix}{text}"
        
        self.chat_display.append(message_html)
        self.input_box.clear()

    def prepare_shared_link(self):
        """
        自动保存分享 URL：从剪贴板获取链接并填入输入框
        对应需求：'输入框自动保存该分享 URL'
        """
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if "http://quant_system/share" in text:
            self.input_box.setText(text)
            self.input_box.setFocus()
