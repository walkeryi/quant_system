import os

HSA_TOKEN = "f3ce3145a0170c3c683fcf83026de94b"

# 数据库配置（务必填写正确密码）
DB_CONFIG = {
    'host': 'localhost',
    'user': 'LH_system',
    'password': '123456',          # 如果密码不是123456，请修改
    'database': 'quant_system',
    'charset': 'utf8mb4'
}
# 数据版本控制：False 表示使用 CSV 版本，True 表示使用数据库版本
USE_DATABASE = False

# 用户文件路径（用于登录模块）
USERS_CSV = os.path.join(os.path.dirname(__file__), "users", "users.csv")

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

STOCK_LIST_CACHE = os.path.join(CACHE_DIR, "stock_list.csv")
TRADE_CALENDAR_CACHE = os.path.join(CACHE_DIR, "trade_calendar.csv")

DAILY_DATA_DIR = os.path.join(CACHE_DIR, "daily")
os.makedirs(DAILY_DATA_DIR, exist_ok=True)

# 分时数据缓存目录
FENSHI_DATA_DIR = os.path.join(CACHE_DIR, "fenshi")
os.makedirs(FENSHI_DATA_DIR, exist_ok=True)