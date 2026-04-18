# -*- coding: utf-8 -*-
"""
聊天模块的数据模型定义
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class MessageType(Enum):
    """消息类型枚举"""
    NORMAL = "normal"          # 普通聊天消息
    STRATEGY_SHARE = "strategy"  # 策略分享
    REPORT_SHARE = "report"      # 报告分享


@dataclass
class ChatMessage:
    """聊天消息数据模型"""
    username: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    message_type: MessageType = MessageType.NORMAL

    @property
    def formatted_time(self) -> str:
        """格式化为 HH:MM:SS 的时间字符串"""
        return self.timestamp.strftime("%H:%M:%S")

    @property
    def is_share(self) -> bool:
        """判断是否为分享消息"""
        return self.message_type != MessageType.NORMAL

    @property
    def prefix(self) -> str:
        """获取消息前缀"""
        prefixes = {
            MessageType.STRATEGY_SHARE: "📢 [策略分享] ",
            MessageType.REPORT_SHARE: "📊 [报告分享] ",
            MessageType.NORMAL: ""
        }
        return prefixes[self.message_type]

    def to_html(self) -> str:
        """转换为 HTML 格式用于显示"""
        colors = {
            MessageType.NORMAL: "#2196F3",          # 蓝色
            MessageType.STRATEGY_SHARE: "#00e676",  # 绿色
            MessageType.REPORT_SHARE: "#00e676"     # 绿色
        }
        color = colors[self.message_type]
        return f"<b style='color:{color};'>[{self.formatted_time}] {self.username}:</b> {self.prefix}{self.content}"

    @classmethod
    def from_text(cls, text: str, username: str = "游客") -> 'ChatMessage':
        """从文本创建消息对象，自动识别消息类型"""
        if "/strategy" in text:
            msg_type = MessageType.STRATEGY_SHARE
        elif "/report" in text:
            msg_type = MessageType.REPORT_SHARE
        else:
            msg_type = MessageType.NORMAL

        return cls(
            username=username,
            content=text,
            message_type=msg_type
        )
