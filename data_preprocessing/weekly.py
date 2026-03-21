# data_preprocessing/weekly.py
import requests
import pandas as pd
from common.utils import setup_logger, log_exceptions
from config import HSA_TOKEN

logger = setup_logger(__name__)

class WeeklyDataProvider:
    """获取沪深个股周线数据"""
    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_zhouxian"

    def __init__(self, token: str = HSA_TOKEN):
        self.token = token

    @log_exceptions(logger)
    def fetch(self, code: str) -> pd.DataFrame | None:
        params = {
            'token': self.token,
            'code': code,
            'all': 0  # 0表示获取最新100笔数据
        }
        try:
            logger.info(f"Fetching weekly data for {code} from API...")
            resp = requests.get(self.API_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get('ret') != 200:
                logger.error(f"Weekly API error for {code}: {data.get('msg')}")
                return None

            records = data.get('data', [])
            if not records:
                return pd.DataFrame()

            df = pd.DataFrame(records)

            # 映射中文拼音列名到标准英文
            column_map = {
                'RiQi': 'date', 'KaiPan': 'open', 'ZuiGao': 'high',
                'ZuiDi': 'low', 'ShouPan': 'close', 'ZongLiang': 'volume',
                'JinE': 'amount'
            }
            df.rename(columns=lambda x: column_map.get(x, x), inplace=True)

            # 价格单位转换 (0.1分 -> 元)
            price_cols = ['open', 'high', 'low', 'close']
            for col in price_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce') / 1000.0

            # 其他数值转换
            if 'volume' in df.columns:
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            if 'amount' in df.columns:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

            df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)

            # 挂载 base 信息
            df.attrs['base'] = {
                'name': data.get('stock_name', ''),
                'code': data.get('stock_code', code)
            }

            return df

        except Exception as e:
            logger.exception(f"Unexpected weekly data error for {code}: {e}")
            return None