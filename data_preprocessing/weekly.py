# quant_system/data_preprocessing/weekly.py
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
            'all': 0  # 严格遵循文档：0表示获取最新100笔数据
        }
        try:
            logger.info(f"正在向周线 API 请求数据: code={code}, all=0")
            resp = requests.get(self.API_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get('ret') != 200:
                logger.error(f"周线 API 错误 ({code}): {data.get('msg')} | 完整响应: {data}")
                return None

            records = data.get('data', [])
            if not records:
                # 【诊断级日志】：用来排查是不是服务端没给数据
                logger.warning(f"【服务端问题】周线接口成功响应(ret=200)，但并未返回100笔数据！服务端真实返回: {data}")
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

            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)

            # 挂载 base 信息
            df.attrs['base'] = {
                'name': data.get('stock_name', ''),
                'code': data.get('stock_code', code)
            }

            return df

        except Exception as e:
            logger.exception(f"周线数据处理发生意外异常 ({code}): {e}")
            return None