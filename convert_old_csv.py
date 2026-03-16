# convert_old_csv.py
import os
import pandas as pd

def convert_csv_to_standard(csv_folder='data/fenshi'):
    """
    将旧格式的 CSV 文件转换为标准格式（列名：time, price, volume）
    转换后的文件会覆盖原文件（建议先备份）。
    """
    if not os.path.exists(csv_folder):
        print(f"文件夹不存在: {csv_folder}")
        return

    files = [f for f in os.listdir(csv_folder) if f.endswith('.csv')]
    converted = 0
    for file in files:
        file_path = os.path.join(csv_folder, file)
        try:
            df = pd.read_csv(file_path)
            # 检查是否已经是标准格式
            required = {'time', 'price', 'volume'}
            if required.issubset(df.columns):
                print(f"跳过 {file}，已经是标准格式")
                continue

            # 定义新旧列名映射（根据实际列名调整）
            col_map = {}
            # 尝试匹配时间列
            time_candidates = ['ShiJian', '时间', 'shijian', 'time']
            for col in df.columns:
                if col in time_candidates:
                    col_map[col] = 'time'
                    break
            # 尝试匹配价格列
            price_candidates = ['JiaGe', '价格', 'jiage', 'price']
            for col in df.columns:
                if col in price_candidates:
                    col_map[col] = 'price'
                    break
            # 尝试匹配成交量列
            volume_candidates = ['ZongLiang', '成交量', 'zongliang', 'volume']
            for col in df.columns:
                if col in volume_candidates:
                    col_map[col] = 'volume'
                    break

            # 检查是否找到必要的列
            if 'time' not in col_map.values() or 'price' not in col_map.values() or 'volume' not in col_map.values():
                print(f"跳过 {file}，无法识别必要列")
                continue

            # 重命名并保留所需列
            df.rename(columns=col_map, inplace=True)
            keep_cols = ['time', 'price', 'volume']
            # 如果有成交额列也保留（可选）
            amount_candidates = ['JinE', '成交额', 'jine', 'amount']
            for col in df.columns:
                if col in amount_candidates:
                    df.rename(columns={col: 'amount'}, inplace=True)
                    keep_cols.append('amount')
                    break

            df = df[keep_cols].copy()
            # 覆盖保存原文件
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"已转换 {file}")
            converted += 1
        except Exception as e:
            print(f"处理 {file} 时出错: {e}")

    print(f"\n转换完成，共处理 {converted} 个文件")

if __name__ == '__main__':
    convert_csv_to_standard()