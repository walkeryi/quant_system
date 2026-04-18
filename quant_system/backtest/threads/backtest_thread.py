# -*- coding: utf-8 -*-
"""
回测执行线程
"""
import sys
import os
import traceback
import pandas as pd
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from contextlib import redirect_stdout, redirect_stderr

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from quant_system.services import BacktestEngine


class EmittingStream:
    def __init__(self, signal):
        self.signal = signal

    def write(self, text):
        if text:
            self.signal.emit(text)

    def flush(self):
        pass


class BacktestThread(QThread):
    finished = pyqtSignal(object, object, list, dict)
    error = pyqtSignal(str)
    log_msg = pyqtSignal(str)
    error_msg = pyqtSignal(str)

    def __init__(self, stock_code, strategy_code, start_date, end_date, initial_capital, stop_loss, quantity=100):
        super().__init__()
        self.stock_code = stock_code
        self.strategy_code = strategy_code
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = float(initial_capital)
        self.stop_loss = float(stop_loss)
        self.quantity = int(quantity)

    def run(self):
        out_stream = EmittingStream(self.log_msg)
        err_stream = EmittingStream(self.error_msg)

        with redirect_stdout(out_stream), redirect_stderr(err_stream):
            try:
                print(f"[引擎调度] 开始获取 {self.stock_code} 的历史数据 ({self.start_date} 至 {self.end_date})...")

                from quant_system.services import DataPreprocessor
                dp = DataPreprocessor()
                df = dp.get_daily_data(self.stock_code, start_date=self.start_date, end_date=self.end_date, all_data=True)

                if df is None or (isinstance(df, str) and df == "DELISTED") or df.empty:
                    raise ValueError(f"无法获取 {self.stock_code} 在指定时间范围的历史数据，请检查代码或网络！")

                if 'date' not in df.columns:
                    df = df.reset_index()

                df['date'] = pd.to_datetime(df['date'])
                df = df.dropna(subset=['close']).sort_values('date').reset_index(drop=True)

                if df.empty:
                    raise ValueError("清洗后的有效数据为空，可能该区间内股票一直处于停牌状态。")

                print(f"[引擎调度] 数据加载成功，共 {len(df)} 条记录。开始编译策略代码...")

                namespace = {'pd': pd, 'np': np}
                exec(self.strategy_code, namespace)

                if 'generate_signals' not in namespace:
                    raise ValueError("策略代码中未找到核心入口函数 `generate_signals(df)`！")

                print("[引擎调度] 正在执行策略信号生成逻辑...")
                func = namespace['generate_signals']
                df = func(df.copy())

                if 'signal' not in df.columns:
                    raise ValueError("策略执行完毕后，返回的数据中未包含关键的 'signal' 信号列！")

                print("[引擎调度] 信号生成完毕！启动极速撮合引擎进行回测...")

                prices = df['close'].values.astype(np.float64)
                signals = df['signal'].values.astype(np.int32)

                if 'pct_chg' in df.columns:
                    limit_ups = ((df['pct_chg'] >= 9.8) & (df['close'] == df['high'])).values.astype(bool)
                    limit_downs = ((df['pct_chg'] <= -9.8) & (df['close'] == df['low'])).values.astype(bool)
                else:
                    limit_ups = np.zeros(len(prices), dtype=bool)
                    limit_downs = np.zeros(len(prices), dtype=bool)

                engine = BacktestEngine(self.initial_capital)
                res = engine.run(prices, signals, limit_ups, limit_downs, self.stop_loss)

                equity_curve = res['equity_curve']
                trades_array = res['trades']

                print("[引擎调度] 撮合完毕！正在计算核心绩效指标...")

                equity_df = pd.DataFrame({
                    'date': df['date'],
                    'equity': equity_curve
                })

                equity_df['total_return'] = (equity_df['equity'] - self.initial_capital) / self.initial_capital * 100
                equity_df['max_equity'] = equity_df['equity'].cummax()
                equity_df['drawdown'] = np.where(
                    equity_df['max_equity'] > 0,
                    (equity_df['equity'] - equity_df['max_equity']) / equity_df['max_equity'] * 100,
                    0.0
                )

                trades = []
                for row in trades_array:
                    idx = int(row[0])
                    trade_type = 'buy' if int(row[1]) == 1 else 'sell'
                    trades.append({
                        'date': df['date'].iloc[idx].strftime('%Y-%m-%d'),
                        'type': trade_type,
                        'price': float(row[2]),
                        'amount': int(row[3])
                    })

                if equity_df.empty:
                    raise ValueError("回测执行完毕，但没有生成任何有效的资产变动记录！")

                final_equity = res['final_equity']
                total_profit = final_equity - self.initial_capital
                total_return = (total_profit / self.initial_capital) * 100 if self.initial_capital > 0 else 0.0
                max_drawdown = float(equity_df['drawdown'].min())

                days = (pd.to_datetime(self.end_date) - pd.to_datetime(self.start_date)).days or 1
                annual_return = (total_return / days) * 365

                equity_series = np.array(equity_curve, dtype=np.float64)
                if len(equity_series) > 1:
                    returns = np.diff(equity_series) / equity_series[:-1]
                    std = np.std(returns)
                    sharpe_ratio = (np.mean(returns) / std * np.sqrt(252)) if std != 0 else 0.0
                    downside_returns = returns[returns < 0]
                    downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 1e-9
                    sortino_ratio = (np.mean(returns) / downside_std * np.sqrt(252))
                else:
                    sharpe_ratio, sortino_ratio = 0.0, 0.0

                winning_trades, gross_profit, gross_loss, completed_trades = 0, 0.0, 0.0, 0
                max_consecutive_losses, current_consecutive_losses = 0, 0
                entry_price = 0.0

                for tr in trades:
                    if tr['type'] == 'buy':
                        entry_price = tr['price']
                    elif tr['type'] == 'sell' and entry_price > 0:
                        completed_trades += 1
                        trade_return = (tr['price'] - entry_price) / entry_price
                        if trade_return > 0:
                            winning_trades += 1
                            gross_profit += trade_return
                            current_consecutive_losses = 0
                        else:
                            gross_loss += abs(trade_return)
                            current_consecutive_losses += 1
                            max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
                        entry_price = 0.0

                win_rate = (winning_trades / completed_trades * 100) if completed_trades > 0 else 0.0
                avg_profit = (gross_profit / winning_trades) if winning_trades > 0 else 0.0
                avg_loss = (gross_loss / (completed_trades - winning_trades)) if (completed_trades - winning_trades) > 0 else 0.0
                pnl_ratio = (avg_profit / avg_loss) if avg_loss > 0 else 0.0

                buy_hold_return = ((prices[-1] - prices[0]) / prices[0] * 100) if len(prices) > 0 else 0.0
                alpha = total_return - buy_hold_return

                metrics = {
                    'total_profit': float(total_profit),
                    'total_return': float(total_return),
                    'annual_return': float(annual_return),
                    'sharpe_ratio': float(sharpe_ratio),
                    'sortino_ratio': float(sortino_ratio),
                    'max_drawdown': max_drawdown,
                    'trade_count': len(trades),
                    'win_rate': float(win_rate),
                    'pnl_ratio': float(pnl_ratio),
                    'max_consecutive_losses': int(max_consecutive_losses),
                    'buy_hold_return': float(buy_hold_return),
                    'alpha': float(alpha)
                }

                print(f"[引擎调度] 指标: 收益率 {total_return:.2f}% (超额 Alpha: {alpha:+.2f}%), 胜率 {win_rate:.2f}%")
                self.finished.emit(df, equity_df, trades, metrics)

            except Exception as e:
                err_trace = traceback.format_exc()
                err_stream.write(err_trace)
                self.error.emit("策略执行异常，请查看左下方【错误清单】！")
