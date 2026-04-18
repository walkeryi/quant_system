# -*- coding: utf-8 -*-
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

    # 使用配置文件中的 LOGS_DIR (指向根目录的 logs)
    try:
        from quant_system.config import LOGS_DIR
        log_dir = LOGS_DIR
    except ImportError:
        # 回退到项目根目录的 logs
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(os.path.dirname(project_root), 'logs')

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
