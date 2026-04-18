# -*- coding: utf-8 -*-
class DataPreprocessingError(Exception):
    """数据预处理模块基础异常"""
    pass

class APIFetchError(DataPreprocessingError):
    """API 获取数据失败异常"""
    pass

class CacheError(DataPreprocessingError):
    """缓存读写异常"""
    pass