# data_preprocessing/fenshi.py
import requests
import pandas as pd
import logging
import pymysql
from pymysql.constants import CLIENT
from config import HSA_TOKEN, DB_CONFIG

logger = logging.getLogger(__name__)


class FenshiDataProvider:
    """获取个股分时数据，并完成单位转换"""

    API_URL = "http://www.sanhulianghua.com:2008/v1/hsa_fenshi"

    def __init__(self, token: str = HSA_TOKEN):
        self.token = token

    def fetch(self, code: str) -> pd.DataFrame | None:
        """
        获取分时数据，返回清洗后的 DataFrame，包含列：
        time, price, avg_price, volume, pct_chg
        并将 base 信息存储在 df.attrs['base'] 中。
        """
        params = {
            'token': self.token,
            'code': code,
            'all': 1
        }
        try:
            logger.info(f"Fetching fenshi data for {code}...")
            resp = requests.get(self.API_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get('ret') != 200:
                error_msg = f"API error for {code}: {data.get('msg')} (ret={data.get('ret')})"
                logger.error(error_msg)
                raise Exception(error_msg)

            base = data.get('base', {})
            points = data.get('data', [])
            if not points:
                logger.warning(f"No fenshi data for {code}")
                return None

            df = pd.DataFrame(points)

            # 单位转换：价格从 0.1分 -> 元，涨幅从 0.001% -> %
            df['price'] = df['JiaGe'] / 1000.0
            df['avg_price'] = df['JunJia'] / 1000.0
            df['pct_chg'] = df['ZhangFu'] / 1000.0
            df['volume'] = df['ZongLiang']  # 单位：手
            df['time'] = df['ShiJian']

            # 保留必要列
            result_df = df[['time', 'price', 'avg_price', 'volume', 'pct_chg']].copy()

            # 附加基础信息
            result_df.attrs['base'] = {
                'name': base.get('name'),
                'code': base.get('code'),
                'date': base.get('date'),
                'zuoshou': base.get('ZuoShou', 0) / 1000.0
            }

            return result_df


        except requests.RequestException as e:

            logger.error(f"Request failed for {code}: {e}")

            raise Exception(f"请求失败: {e}")  # 抛出异常

        except Exception as e:

            logger.exception(f"Unexpected error for {code}: {e}")

            raise  # 重新抛出原异常

    def save_to_db(self, df: pd.DataFrame) -> int:
        """将分时数据保存到 MySQL 数据库"""
        base = df.attrs.get('base', {})
        code = base.get('code')
        trade_date = base.get('date')
        if not code or not trade_date:
            logger.error("DataFrame 缺少 code 或 date 信息，无法存入数据库")
            return 0

        records = []
        for _, row in df.iterrows():
            time_str = str(row['time']).strip()
            if len(time_str) == 5:
                time_str += ":00"
            records.append((
                code,
                trade_date,
                time_str,
                float(row['price']),
                int(row['volume']),
                float(row['price'] * row['volume'] * 100)  # 成交额（元）
            ))

        connection = None
        try:
            connection = pymysql.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database'],
                charset=DB_CONFIG['charset'],
                client_flag=CLIENT.MULTI_STATEMENTS
            )
            with connection.cursor() as cursor:
                sql = """
                      INSERT IGNORE INTO fenshi_data
                          (code, trade_date, time, price, volume, amount)
                      VALUES (%s, %s, %s, %s, %s, %s) \
                      """
                cursor.executemany(sql, records)
                connection.commit()
                inserted = cursor.rowcount
                logger.info(f"Inserted {inserted} records into fenshi_data for {code} {trade_date}")
                return inserted
        except Exception as e:
            logger.exception(f"Failed to save fenshi data to DB: {e}")
            if connection:
                connection.rollback()
            return 0
        finally:
            if connection:
                connection.close()