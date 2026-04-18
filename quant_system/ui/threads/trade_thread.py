# -*- coding: utf-8 -*-
# ui/threads/trade_thread.py

from PyQt6.QtCore import QThread, pyqtSignal

from quant_system.services import TraderAPI



class TradeThread(QThread):

    finished = pyqtSignal(dict)



    def __init__(self, endpoint, code, price, hand, policy, parent=None):

        super().__init__(parent)

        self.endpoint = endpoint

        self.code = code

        self.price = price

        self.hand = hand

        self.policy = policy



    def run(self):

        res = TraderAPI.execute(self.endpoint, self.code, self.price, self.hand, self.policy)

        self.finished.emit(res)