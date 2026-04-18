# -*- coding: utf-8 -*-
"""
聊天客户端：负责消息的发送、接收和广播管理
"""
import socket
import threading
import json
from typing import Optional, Callable
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

from .models import ChatMessage, MessageType


class ChatClient(QObject):
    """聊天客户端，支持本地回显和网络通信"""
    message_received = pyqtSignal(object)  # ChatMessage 信号
    connection_changed = pyqtSignal(bool)  # 连接状态信号

    def __init__(self, host: str = "127.0.0.1", port: int = 9999):
        super().__init__()
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """连接到聊天服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self.running = True
            self.connection_changed.emit(True)

            # 启动接收线程
            thread = threading.Thread(target=self._receive_loop, daemon=True)
            thread.start()
            return True
        except Exception as e:
            print(f"[聊天客户端] 连接失败: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """断开连接"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
        self.connected = False
        self.connection_changed.emit(False)

    def send_message(self, content: str, username: str = "游客") -> bool:
        """发送消息"""
        if not self.connected or not self.socket:
            return False

        msg = ChatMessage.from_text(content, username)

        try:
            data = {
                "username": msg.username,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "type": msg.message_type.value
            }
            self.socket.sendall(json.dumps(data).encode("utf-8"))
            return True
        except Exception as e:
            print(f"[聊天客户端] 发送失败: {e}")
            return False

    def _receive_loop(self):
        """接收消息循环"""
        while self.running and self.socket:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break

                msg_data = json.loads(data.decode("utf-8"))
                msg = ChatMessage(
                    username=msg_data["username"],
                    content=msg_data["content"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    message_type=MessageType(msg_data.get("type", "normal"))
                )
                self.message_received.emit(msg)
            except Exception as e:
                print(f"[聊天客户端] 接收错误: {e}")
                break

        self.disconnect()

    @property
    def is_connected(self) -> bool:
        return self.connected


class MockChatClient(ChatClient):
    """模拟聊天客户端（用于离线模式）"""

    def connect(self) -> bool:
        """模拟连接"""
        self.connected = True
        self.connection_changed.emit(True)
        return True

    def send_message(self, content: str, username: str = "游客") -> bool:
        """模拟发送（仅本地记录）"""
        msg = ChatMessage.from_text(content, username)
        self.message_received.emit(msg)
        return True
