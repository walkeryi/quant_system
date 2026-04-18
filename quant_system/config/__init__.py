# -*- coding: utf-8 -*-
import os
# BASE_DIR 指向项目根目录 (quant_system 的上一级)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
USE_DATABASE = False

# HSA API Token
HSA_TOKEN = "f3ce3145a0170c3c683fcf83026de94b"

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'LH_system',
    'password': '123456',
    'database': 'quant_system',
    'charset': 'utf8mb4'
}

# 用户文件路径
USERS_DIR = os.path.join(BASE_DIR, 'users')
USERS_CSV = os.path.join(USERS_DIR, 'users.csv')

# 缓存路径
STOCK_LIST_CACHE = os.path.join(CACHE_DIR, "stock_list.parquet")
TRADE_CALENDAR_CACHE = os.path.join(CACHE_DIR, "trade_calendar.csv")

DAILY_DATA_DIR = os.path.join(CACHE_DIR, "daily")
os.makedirs(DAILY_DATA_DIR, exist_ok=True)

FENSHI_DATA_DIR = os.path.join(CACHE_DIR, "fenshi")
os.makedirs(FENSHI_DATA_DIR, exist_ok=True)

# 日志目录
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)
