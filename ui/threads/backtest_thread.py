# ui/threads/backtest_thread.py
import traceback
import pandas as pd
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from data_preprocessing.fetcher import DataPreprocessor


class BacktestThread(QThread):
    # 定义信号：回传 (行情数据框, 资金数据框, 交易记录列表, 统计指标字典)
    finished = pyqtSignal(object, object, list, dict)
    error = pyqtSignal(str)

    def __init__(self, stock_code, strategy_code, start_date, end_date, initial_capital, stop_loss):
        super().__init__()
        self.stock_code = stock_code
        self.strategy_code = strategy_code
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = float(initial_capital)
        self.stop_loss = float(stop_loss)

    def run(self):
        try:
            # ================= 1. 获取回测区间历史数据 =================
            dp = DataPreprocessor()
            df = dp.get_daily_data(self.stock_code, start_date=self.start_date, end_date=self.end_date, all_data=True)

            if df is None or (isinstance(df, str) and df == "DELISTED") or df.empty:
                self.error.emit(f"无法获取 {self.stock_code} 在指定时间范围的历史数据，请检查代码或网络！")
                return

            # 【修复核心错误1：索引转换问题】确保 date 是一列而不是单独的 index
            if 'date' not in df.columns:
                df = df.reset_index()

            # 防御性校验
            if 'date' not in df.columns or 'close' not in df.columns:
                self.error.emit(f"数据源结构异常，缺失关键列。当前列名: {df.columns.tolist()}")
                return

            # 确保日期列格式正确并按时间升序排列，同时清除价格为 NaN 的异常数据
            df['date'] = pd.to_datetime(df['date'])
            df = df.dropna(subset=['close']).sort_values('date').reset_index(drop=True)

            if df.empty:
                self.error.emit("清洗后的有效数据为空，可能该区间内股票一直处于停牌状态。")
                return

            # ================= 2. 动态编译并执行用户编写的策略 =================
            # 创建纯净的命名空间，注入 pandas 和 numpy
            namespace = {'pd': pd, 'np': np}
            try:
                exec(self.strategy_code, namespace)
            except Exception as e:
                self.error.emit(f"策略编译失败，存在语法错误：\n{str(e)}")
                return

            if 'generate_signals' not in namespace:
                self.error.emit("策略代码中未找到核心入口函数 `generate_signals(df)`！")
                return

            func = namespace['generate_signals']
            try:
                # 把历史数据传给用户的策略进行运算，生成买卖信号
                df = func(df.copy())
            except Exception as e:
                self.error.emit(f"策略运行期间崩溃，请检查您的策略代码逻辑：\n{traceback.format_exc()}")
                return

            if 'signal' not in df.columns:
                self.error.emit("策略执行完毕后，返回的数据中未包含关键的 'signal' 信号列！")
                return

            # ================= 3. 回测引擎：模拟撮合与资金计算 =================
            cash = self.initial_capital
            holdings = 0
            buy_price = 0.0

            equity_records = []
            trades = []

            max_equity = cash

            # 模拟时间回流，逐日遍历
            for i, row in df.iterrows():
                current_date = row['date']
                current_price = float(row['close'])
                signal = row.get('signal', 0)

                # 剔除无效价格以防除零报错
                if current_price <= 0 or pd.isna(current_price):
                    continue

                # --- 止损拦截逻辑 ---
                # 【修复核心错误2：增加 buy_price > 0 判断防止除 0 异常】
                if holdings > 0 and self.stop_loss > 0 and buy_price > 0:
                    loss_pct = (current_price - buy_price) / buy_price * 100
                    if loss_pct <= -self.stop_loss:
                        signal = -1  # 强制熔断，触发卖出信号

                # --- 撮合买入逻辑 ---
                if signal == 1 and cash >= current_price * 100:
                    # 全仓买入（按100股的整数倍计算最大可买手数）
                    max_shares = int(cash // (current_price * 100)) * 100
                    if max_shares > 0:
                        cost = max_shares * current_price
                        cash -= cost
                        holdings += max_shares
                        buy_price = current_price
                        trades.append({
                            'date': current_date.strftime('%Y-%m-%d'),
                            'type': 'buy',
                            'price': current_price,
                            'amount': max_shares
                        })

                # --- 撮合卖出逻辑 ---
                elif signal == -1 and holdings > 0:
                    # 清仓卖出
                    revenue = holdings * current_price
                    cash += revenue
                    trades.append({
                        'date': current_date.strftime('%Y-%m-%d'),
                        'type': 'sell',
                        'price': current_price,
                        'amount': holdings
                    })
                    holdings = 0
                    buy_price = 0.0

                # --- 每日盘后清算 ---
                current_equity = cash + holdings * current_price
                max_equity = max(max_equity, current_equity)  # 记录历史最高资产

                # 【修复核心错误3：资产回撤计算除0防御】
                drawdown = ((current_equity - max_equity) / max_equity * 100) if max_equity > 0 else 0.0

                equity_records.append({
                    'date': current_date,
                    'equity': current_equity,
                    'total_return': ((
                                                 current_equity - self.initial_capital) / self.initial_capital * 100) if self.initial_capital > 0 else 0.0,
                    'drawdown': drawdown
                })

            # 防御无记录生成的崩溃
            if not equity_records:
                self.error.emit("回测执行完毕，但没有生成任何有效的资产变动记录！")
                return

            equity_df = pd.DataFrame(equity_records)

            # ================= 4. 统计策略综合绩效指标 =================
            final_equity = equity_df['equity'].iloc[-1]
            total_return = (
                                       final_equity - self.initial_capital) / self.initial_capital * 100 if self.initial_capital > 0 else 0.0
            max_drawdown = equity_df['drawdown'].min()  # 回撤已经是负数，取 min 即可

            metrics = {
                'final_equity': final_equity,
                'total_return': total_return,
                'max_drawdown': max_drawdown,
                'trade_count': len(trades)
            }

            # ================= 5. 将结果发送给图表和 UI 更新 =================
            self.finished.emit(df, equity_df, trades, metrics)

        except Exception as e:
            self.error.emit(f"回测引擎遭遇底层严重错误：\n{traceback.format_exc()}")