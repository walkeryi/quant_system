import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name='quant_system', log_file='quant_system.log', level=logging.INFO):
    """设置全局日志器，输出到文件和控制台"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # 避免重复配置

    logger.setLevel(level)

    # 文件处理器（按大小轮转，保留3个备份）
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)
    file_handler = RotatingFileHandler(log_path, maxBytes=10*1024*1024, backupCount=3, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

    return logger

# 全局异常钩子
def global_exception_handler(exctype, value, tb):
    """全局未捕获异常处理"""
    logger = logging.getLogger('quant_system')
    logger.critical("Unhandled exception", exc_info=(exctype, value, tb))
    # 可选：弹出错误对话框
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        if QApplication.instance() is not None:
            error_msg = ''.join(traceback.format_exception(exctype, value, tb))
            QMessageBox.critical(None, "程序错误", f"发生未预期的错误，请查看日志文件。\n{value}")
    except:
        pass
    sys.__excepthook__(exctype, value, tb)  # 调用默认钩子

# 安装全局异常钩子
sys.excepthook = global_exception_handler