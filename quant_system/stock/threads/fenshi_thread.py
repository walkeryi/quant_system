# -*- coding: utf-8 -*-
"""
分时数据加载线程
"""
import logging
from PyQt6.QtCore import QThread, pyqtSignal
from quant_system.services import DataPreprocessor

logger = logging.getLogger('quant_system')


class FenshiDataThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, code):
        super().__init__()
        self.code = code

    def run(self):
        try:
            dp = DataPreprocessor()
            df = dp.get_fenshi_data(self.code)
            logger.info(f"[Thread] code={self.code} received df type={type(df).__name__} "
                        f"is_empty={df.empty if hasattr(df, 'empty') else 'N/A'}")

            if isinstance(df, str) and df == "DELISTED":
                logger.warning(f"[Thread] code={self.code} 返回 DELISTED")
                self.error.emit("302_DELISTED")
                return

            if df is None or (hasattr(df, 'empty') and df.empty):
                logger.warning(f"[Thread] code={self.code} 返回空数据 df={df}")
                self.error.emit("无法获取分时数据")
                return
            logger.info(f"[Thread] code={self.code} 发送 finished 信号，columns={list(df.columns) if hasattr(df, 'columns') else 'N/A'}")
            self.finished.emit(df)
        except Exception as e:
            logger.exception(f"[Thread] code={self.code} 异常: {e}")
            if "302" in str(e):
                self.error.emit("302_DELISTED")
            else:
                self.error.emit(str(e))
