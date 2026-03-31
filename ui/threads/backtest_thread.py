# 文件路径: quant_system/ui/threads/backtest_thread.py
import traceback
import pandas as pd
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from data_preprocessing.fetcher import DataPreprocessor

# 导入编译好的 C++ 核心库
try:
    import backtest_core
except ImportError:
    raise ImportError("无法导入 backtest_core C++ 模块，请确认已运行 python setup.py build_ext --inplace 进行编译！")


class BacktestThread(QThread):
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

            if 'date' not in df.columns:
                df = df.reset_index()

            if 'date' not in df.columns or 'close' not in df.columns:
                self.error.emit(f"数据源结构异常，缺失关键列。当前列名: {df.columns.tolist()}")
                return

            df['date'] = pd.to_datetime(df['date'])
            df = df.dropna(subset=['close']).sort_values('date').reset_index(drop=True)

            if df.empty:
                self.error.emit("清洗后的有效数据为空，可能该区间内股票一直处于停牌状态。")
                return

            # ================= 2. 动态编译并执行用户编写的策略 =================
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
                df = func(df.copy())
            except Exception as e:
                self.error.emit(f"策略运行期间崩溃：\n{traceback.format_exc()}")
                return

            if 'signal' not in df.columns:
                self.error.emit("策略执行完毕后，返回的数据中未包含关键的 'signal' 信号列！")
                return

            # ================= 3. 调用 C++ 高性能回测引擎 =================
            # 将 DataFrame 转换为 C++ 能直接通过指针读取的 Numpy 连续内存数组
            prices = df['close'].values.astype(np.float64)
            signals = df['signal'].values.astype(np.int32)

            engine = backtest_core.BacktestEngine(self.initial_capital)

            # C++ 极速撮合计算核心 (此过程 GIL 已释放)
            res = engine.run(prices, signals, self.stop_loss)

            equity_curve = res['equity_curve']
            trades_array = res['trades']

            # ================= 4. 结果反序列化与高级指标计算 (向量化) =================
            # 利用 Pandas 的底层向量化能力快速计算回撤和收益，避免在 Python 中写循环
            equity_df = pd.DataFrame({
                'date': df['date'],
                'equity': equity_curve
            })

            # 计算总收益率序列
            equity_df['total_return'] = (equity_df['equity'] - self.initial_capital) / self.initial_capital * 100

            # 向量化计算最大回撤
            equity_df['max_equity'] = equity_df['equity'].cummax()
            equity_df['drawdown'] = np.where(
                equity_df['max_equity'] > 0,
                (equity_df['equity'] - equity_df['max_equity']) / equity_df['max_equity'] * 100,
                0.0
            )

            # 解析 C++ 返回的交易记录矩阵
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
                self.error.emit("回测执行完毕，但没有生成任何有效的资产变动记录！")
                return

            # ================= 5. 组装最终绩效评价指标 =================
            final_equity = res['final_equity']
            total_return = (
                                       final_equity - self.initial_capital) / self.initial_capital * 100 if self.initial_capital > 0 else 0.0
            max_drawdown = equity_df['drawdown'].min()

            metrics = {
                'final_equity': final_equity,
                'total_return': total_return,
                'max_drawdown': max_drawdown,
                'trade_count': len(trades)
            }

            self.finished.emit(df, equity_df, trades, metrics)

        except Exception as e:
            self.error.emit(f"回测引擎遭遇底层严重错误：\n{traceback.format_exc()}")