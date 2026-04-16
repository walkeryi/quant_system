# -*- coding: utf-8 -*-



# -*- coding: utf-8 -*-

# 鏂囦欢璺緞: quant_system/ui/ui_events.py

from PyQt6.QtCore import QObject, pyqtSignal



class GlobalUIEventBus(QObject):

    ""


    stock_selected = pyqtSignal(str)          # 褰撶敤鎴峰湪浠讳綍鍦版柟閫変腑浜嗕竴鍙偂绁ㄦ椂瑙﹀彂

    backtest_requested = pyqtSignal(str)      # 璇锋眰璺宠浆鍒板洖娴嬮〉闈㈠苟濉叆鑲＄エ

    global_log_msg = pyqtSignal(str, str)     # 鍙戦€佸叏灞€鏃ュ織 (绾у埆, 鍐呭)



# 瀹炰緥鍖栦负鍗曚緥锛屾暣涓?UI 鍏变韩杩欎竴涓ぇ鍠囧彮

EVENT_BUS = GlobalUIEventBus()



