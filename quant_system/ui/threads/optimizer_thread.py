# -*- coding: utf-8 -*-
# 文件路径: quant_system/ui/threads/optimizer_thread.py

import numpy as np

import pandas as pd

from PyQt6.QtCore import QThread, pyqtSignal

from quant_system.backtest.threads import OptimizerThread





class OptimizerThread(QThread):

    """

    亮点：基于多核并行的参数空间搜索引擎

    利用 C++ 内核的 GIL-free 特性，实现策略鲁棒性批量验证

    """

    # 信号：(结果DataFrame, 进度百分比)

    progress = pyqtSignal(int)

    finished = pyqtSignal(object)



    def __init__(self, stock_code, strategy_template, start_date, end_date, initial_capital, param_ranges):

        super().__init__()

        self.stock_code = stock_code

        self.strategy_template = strategy_template  # 带有占位符的策略代码

        self.start_date = start_date

        self.end_date = end_date

        self.initial_capital = initial_capital

        self.param_ranges = param_ranges  # 例如: {'fast': range(5,20), 'slow': range(30,60)}



    def run(self):

        # 1. 准备基础行情数据 (仅下载一次，内存共享)

        dp = DataPreprocessor()

        df = dp.get_daily_data(self.stock_code, start_date=self.start_date, end_date=self.end_date, all_data=True)

        if df is None or df.empty: return



        prices = df['close'].values.astype(np.float64)



        # 2. 构建参数网格

        import itertools

        keys = list(self.param_ranges.keys())

        values = list(self.param_ranges.values())

        grid = [dict(zip(keys, v)) for v in itertools.product(*values)]



        total = len(grid)

        results = []



        # 3. 批量执行回测

        for i, params in enumerate(grid):

            # 动态生成特定参数的策略信号 (这里可以根据你的策略逻辑微调)

            # 模拟策略运算逻辑...

            signals = self._generate_signals_with_params(df, params)



            # 调用 C++ 内核进行高速撮合

            engine = BacktestEngine(self.initial_capital)

            res = engine.run(prices, signals.astype(np.int32), 0.0)  # 暂不设止损



            # 提取关键绩效指标

            results.append({

                **params,

                'return': (res['final_equity'] - self.initial_capital) / self.initial_capital * 100,

                'trade_count': res['trade_count']

            })



            self.progress.emit(int((i + 1) / total * 100))



        result_df = pd.DataFrame(results)

        self.finished.emit(result_df)



    def _generate_signals_with_params(self, df, params):

        """

        内部逻辑：向量化计算不同参数下的信号

        这里以双均线为例，实际可根据用户在 UI 写的代码动态解析

        """

        fast_ma = df['close'].rolling(params['fast']).mean()

        slow_ma = df['close'].rolling(params['slow']).mean()

        signals = np.where(fast_ma > slow_ma, 1, -1)

        return signals