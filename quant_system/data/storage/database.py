# -*- coding: utf-8 -*-
"""
SQLite 数据库管理
"""
import os
import sqlite3
import pandas as pd
from datetime import datetime
from quant_system.config import CACHE_DIR

DB_PATH = os.path.join(CACHE_DIR, "stock_quotes.db")


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-2000;")
    return conn


class DBManager:
    """数据库管理器"""
    DB_PATH = DB_PATH

    @staticmethod
    def _get_conn():
        return _get_conn()

    @staticmethod
    def init():
        init_db()


def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_list (
                code TEXT PRIMARY KEY,
                name TEXT,
                price REAL,
                pct_chg REAL,
                high REAL,
                low REAL,
                volume REAL,
                last_update TEXT
            )
        """)
        conn.commit()


def upsert_stock_quote(code, name=None, price=None, pct_chg=None, high=None, low=None, volume=None, last_update=None):
    init_db()
    ts = last_update or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO stock_list (code, name, price, pct_chg, high, low, volume, last_update)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name = COALESCE(excluded.name, stock_list.name),
                price = COALESCE(excluded.price, stock_list.price),
                pct_chg = COALESCE(excluded.pct_chg, stock_list.pct_chg),
                high = COALESCE(excluded.high, stock_list.high),
                low = COALESCE(excluded.low, stock_list.low),
                volume = COALESCE(excluded.volume, stock_list.volume),
                last_update = excluded.last_update
        """, (str(code).zfill(6), name, price, pct_chg, high, low, volume, ts))
        conn.commit()


def bulk_upsert_from_df(df):
    if df is None or df.empty:
        return
    init_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for _, row in df.iterrows():
        code = str(row.get("code", "")).zfill(6)
        if not code or code == "000000":
            continue
        rows.append((
            code,
            row.get("name"),
            _to_float(row.get("price")),
            _to_float(row.get("pct_chg")),
            _to_float(row.get("high")),
            _to_float(row.get("low")),
            _to_float(row.get("volume")),
            now,
        ))
    if not rows:
        return
    with _get_conn() as conn:
        conn.executemany("""
            INSERT INTO stock_list (code, name, price, pct_chg, high, low, volume, last_update)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name = COALESCE(excluded.name, stock_list.name),
                price = COALESCE(excluded.price, stock_list.price),
                pct_chg = COALESCE(excluded.pct_chg, stock_list.pct_chg),
                high = COALESCE(excluded.high, stock_list.high),
                low = COALESCE(excluded.low, stock_list.low),
                volume = COALESCE(excluded.volume, stock_list.volume),
                last_update = excluded.last_update
        """, rows)
        conn.commit()


def load_stock_list_df():
    init_db()
    with _get_conn() as conn:
        df = pd.read_sql_query("""
            SELECT code, name, price, pct_chg, high, low, volume, last_update
            FROM stock_list
            ORDER BY code
        """, conn)
    return df


def get_latest_update_date():
    init_db()
    with _get_conn() as conn:
        row = conn.execute("SELECT MAX(last_update) FROM stock_list").fetchone()
    if not row or not row[0]:
        return None
    return str(row[0])[:10]


def _to_float(v):
    if v is None:
        return None
    if isinstance(v, str) and (not v.strip() or v.strip() == "--"):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
