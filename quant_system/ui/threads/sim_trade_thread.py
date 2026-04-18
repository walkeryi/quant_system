# -*- coding: utf-8 -*-
# 文件路径: quant_system/ui/threads/sim_trade_thread.py
import time
from PyQt6.QtCore import QThread, pyqtSignal
from quant_system.services import SimTradeEngine as SimTradeEngineBase

class SimTradeThread(QThread):
    update_signal = pyqtSignal(dict, list, str)

    def __init__(self):
        super().__init__()
        self.engine = SimTradeEngine()
        self.engine.update_signal.connect(self._forward_signal)
        self.is_running = True

    def _forward_signal(self, metrics, recs, log_msg):
        self.update_signal.emit(metrics, recs, log_msg)

    def run(self):
        self.engine.is_running = True
        self.engine.start()

    def stop(self):
        self.is_running = False
        self.engine.stop()
        self.engine.wait()