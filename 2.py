import os
import sys
import pandas as pd
import pymysql
from pymysql.constants import CLIENT

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG

def import_csv_to_db(csv_folder='cache/fenshi'):
    if not os.path.exists(csv_folder):
        print(f"文件夹不存在: {csv_folder}")
        return

    files = [f for f in os.listdir(csv_folder) if f.endswith('.csv')]
    if not files:
        print("没有找到 CSV 文件")
        return

    try:
        connection = pymysql.connect(**DB_CONFIG, client_flag=CLIENT.MULTI_STATEMENTS)
        print("数据库连接成功")
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return

    total_inserted = 0
    try:
        with connection.cursor() as cursor:
            for file in files:
                file_path = os.path.join(csv_folder, file)
                base_name = os.path.splitext(file)[0]
                parts = base_name.split('_')
                if len(parts) != 2:
                    print(f"跳过文件名格式不正确: {file}")
                    continue
                code, date = parts
                print(f"\n正在处理文件: {file}")

                try:
                    df = pd.read_csv(file_path)
                    # 直接使用标准列名
                    required = ['time', 'price', 'volume']
                    if not all(col in df.columns for col in required):
                        print(f"文件缺少必要列，跳过")
                        continue
                except Exception as e:
                    print(f"读取文件失败: {e}")
                    continue

                # 确保数值类型
                df['price'] = pd.to_numeric(df['price'], errors='coerce')
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
                df = df.dropna(subset=['price', 'volume'])
                if df.empty:
                    print(f"没有有效数据，跳过")
                    continue

                records = []
                for idx, row in df.iterrows():
                    time_str = str(row['time']).strip()
                    if len(time_str) == 5:
                        time_str += ":00"
                    price_val = float(row['price'])
                    volume_val = int(row['volume'])
                    amount_val = price_val * volume_val * 100

                    records.append((
                        str(code),
                        str(date),
                        str(time_str),
                        price_val,
                        volume_val,
                        amount_val
                    ))

                sql = """
                    INSERT IGNORE INTO fenshi_data 
                    (code, trade_date, time, price, volume, amount)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.executemany(sql, records)
                connection.commit()
                inserted = cursor.rowcount
                total_inserted += inserted
                print(f"已导入 {file}: {inserted} 条记录")
    except Exception as e:
        print(f"导入异常: {e}")
        connection.rollback()
    finally:
        connection.close()
        print(f"\n总共导入 {total_inserted} 条记录")

if __name__ == '__main__':
    import_csv_to_db()