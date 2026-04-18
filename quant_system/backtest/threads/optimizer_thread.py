# -*- coding: utf-8 -*-
"""
参数优化线程
"""
import numpy as np
import pandas as pd
import itertools
from PyQt6.QtCore import QThread, pyqtSignal
from quant_system.services import BacktestEngine, DataPreprocessor


class OptimizerThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)

    def __init__(self, stock_code, strategy_template, start_date, end_date, initial_capital, param_ranges):
        super().__init__()
        self.stock_code = stock_code
        self.strategy_template = strategy_template
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.param_ranges = param_ranges

    def run(self):
        dp = DataPreprocessor()
        df = dp.get_daily_data(self.stock_code, start_date=self.start_date, end_date=self.end_date, all_data=True)
        if df is None or df.empty:
            return

        prices = df['close'].values.astype(np.float64)

        keys = list(self.param_ranges.keys())
        values = list(self.param_ranges.values())
        grid = [dict(zip(keys, v)) for v in itertools.product(*values)]

        total = len(grid)
        results = []

        for i, params in enumerate(grid):
            signals = self._generate_signals_with_params(df, params)
            engine = BacktestEngine(self.initial_capital)
            res = engine.run(prices, signals.astype(np.int32), 0.0, 0.0, 0.0)

            results.append({
                **params,
                'return': (res['final_equity'] - self.initial_capital) / self.initial_capital * 100,
                'trade_count': res['trade_count']
            })

            self.progress.emit(int((i + 1) / total * 100))

        result_df = pd.DataFrame(results)
        self.finished.emit(result_df)

    def _generate_signals_with_params(self, df, params):
        fast_ma = df['close'].rolling(params['fast']).mean()
        slow_ma = df['close'].rolling(params['slow']).mean()
        signals = np.where(fast_ma > slow_ma, 1, -1)
        return signals
