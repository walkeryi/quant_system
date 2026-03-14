import os

HSA_TOKEN = "f3ce3145a0170c3c683fcf83026de94b"

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

STOCK_LIST_CACHE = os.path.join(CACHE_DIR, "stock_list.csv")
TRADE_CALENDAR_CACHE = os.path.join(CACHE_DIR, "trade_calendar.csv")

# 日线数据缓存目录
DAILY_DATA_DIR = os.path.join(CACHE_DIR, "daily")
os.makedirs(DAILY_DATA_DIR, exist_ok=True)