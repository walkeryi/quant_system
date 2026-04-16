# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
# 鏂囦欢璺緞: quant_system/ui/threads/sim_trade_thread.py
import time
from PyQt6.QtCore import QThread, pyqtSignal
from core.sim_engine import SimulationEngine

class SimTradeThread(QThread):
    ""
    update_signal = pyqtSignal(dict, list, str)
    
    def __init__(self):
        super().__init__()
        self.engine = SimulationEngine()
        self.is_running = True

    def run(self):
        while self.is_running:
            # 璋冪敤搴曞眰鏍稿績寮曟搸
            metrics, recs, log_msg = self.engine.tick()
            
            if log_msg != "NOT_RUNNING":
                self.update_signal.emit(metrics, recs, log_msg)
            
            # 浼戠湢 10 绉掑悗杩涜涓嬩竴娆¤疆璇?            self._safe_sleep(10)

    def _safe_sleep(self, seconds):
        ""
        for _ in range(seconds * 2):
            if not self.is_running: break
            time.sleep(0.5)

    def stop(self):
        self.is_running = False

