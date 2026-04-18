# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from functools import wraps
logger = logging.getLogger('quant_system')

def setup_logger(name=__name__, level=logging.INFO, log_file=None):
    """设置日志记录器，可输出到文件和/or控制台"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # 避免重复添加handler

    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 控制台handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # 文件handler（可选）
    if log_file:
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger

def log_exceptions(logger=None):
    """装饰器：记录函数抛出的异常"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = setup_logger(func.__module__)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {e}")
                raise
        return wrapper
    return decorator

def validate_date(date_str):
    """验证日期字符串格式 YYYY-MM-DD，返回datetime对象或None"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return None

def date_to_str(date_obj):
    """将datetime对象转换为 YYYY-MM-DD 格式字符串"""
    return date_obj.strftime('%Y-%m-%d') if date_obj else None