import os
import pandas as pd
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem
from PyQt6.QtCore import Qt

def fill_fenshi_table(table: QTableWidget, df: pd.DataFrame):
    table.setRowCount(len(df))
    for i, row in enumerate(df[::-1].itertuples()):
        table.setItem(i, 0, QTableWidgetItem(row.time))
        table.setItem(i, 1, QTableWidgetItem(f"{row.price:.2f}"))
        table.setItem(i, 2, QTableWidgetItem(f"{row.avg_price:.2f}"))
        table.setItem(i, 3, QTableWidgetItem(str(row.volume)))
        chg_item = QTableWidgetItem(f"{row.pct_chg:+.2f}%")
        if row.pct_chg > 0:
            chg_item.setForeground(Qt.GlobalColor.red)
        elif row.pct_chg < 0:
            chg_item.setForeground(Qt.GlobalColor.green)
        table.setItem(i, 4, chg_item)

def fill_daily_table(table: QTableWidget, df: pd.DataFrame):
    df_display = df.tail(100).iloc[::-1]
    table.setRowCount(len(df_display))
    for i, (date, row) in enumerate(df_display.iterrows()):
        table.setItem(i, 0, QTableWidgetItem(date.strftime('%Y-%m-%d')))
        table.setItem(i, 1, QTableWidgetItem(f"{row['close']:.2f}"))
        table.setItem(i, 2, QTableWidgetItem("--"))
        table.setItem(i, 3, QTableWidgetItem(str(int(row['volume']))))
        table.setItem(i, 4, QTableWidgetItem("--"))

def save_fenshi_csv(df: pd.DataFrame, base: dict):
    path = "cache/fenshi"
    os.makedirs(path, exist_ok=True)
    file_path = f"{path}/{base.get('code')}_{base.get('date')}.csv"
    df.to_csv(file_path, index=False, encoding='utf-8-sig')