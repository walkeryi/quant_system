# data_preprocessing/cleaner.py
import pandas as pd
import numpy as np

def standardize_columns(df, column_map):
    """
    将 DataFrame 的列名按照映射表标准化
    :param df: 原始 DataFrame
    :param column_map: 字典，如 {'日期': 'date', '开盘': 'open'}
    :return: 重命名后的 DataFrame
    """
    return df.rename(columns=column_map)

def handle_missing(df, method='ffill', limit=None):
    """
    处理缺失值
    :param method: 'ffill' 前向填充, 'bfill' 后向填充, 'drop' 删除, 'interpolate' 插值
    :param limit: 填充或插值的最大连续缺失数
    """
    if method == 'ffill':
        return df.fillna(method='ffill', limit=limit)
    elif method == 'bfill':
        return df.fillna(method='bfill', limit=limit)
    elif method == 'drop':
        return df.dropna()
    elif method == 'interpolate':
        return df.interpolate(limit=limit)
    else:
        return df

def ensure_numeric(df, columns):
    """确保指定列为数值类型"""
    for col in columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def set_date_index(df, date_col='date'):
    """将日期列设为索引并排序"""
    df[date_col] = pd.to_datetime(df[date_col])
    df.set_index(date_col, inplace=True)
    df.sort_index(inplace=True)
    return df