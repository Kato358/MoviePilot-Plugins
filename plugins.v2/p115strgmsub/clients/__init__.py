"""
客户端模块
包含115网盘、Telegram等客户端
"""
from .p115 import P115ClientManager
from .telegram import TelegramClient

__all__ = [
    "P115ClientManager",
    "TelegramClient",
]
