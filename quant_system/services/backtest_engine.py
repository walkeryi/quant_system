# -*- coding: utf-8 -*-
"""
回测撮合引擎
"""
import numpy as np


class BacktestEngine:
    """
    高性能回测撮合引擎
    支持涨跌停限制、滑点、佣金、印花税
    """

    def __init__(self, initial_capital: float):
        self.capital = float(initial_capital)
        self.holdings = 0
        self.buy_price = 0.0
        self.commission_rate = 0.00025
        self.stamp_duty = 0.0005
        self.slippage_pct = 0.001
        self.min_commission = 5.0

    def run(self, prices, signals, limit_ups, limit_downs, stop_loss_pct):
        capital = self.capital
        holdings = self.holdings
        buy_price = self.buy_price

        n = len(prices)
        equity_curve = [0.0] * n
        trades = []
        trade_count = 0
        final_price = 0.0

        if n > 0:
            for i in range(n):
                cur_price = float(prices[i])
                signal = int(signals[i])
                is_limit_up = bool(limit_ups[i]) if hasattr(limit_ups, '__getitem__') else False
                is_limit_down = bool(limit_downs[i]) if hasattr(limit_downs, '__getitem__') else False

                if holdings > 0 and stop_loss_pct > 0:
                    if (cur_price - buy_price) / buy_price * 100.0 <= -stop_loss_pct:
                        signal = -1

                if signal == 1 and holdings == 0:
                    if not is_limit_up:
                        actual_buy_price = cur_price * (1 + self.slippage_pct)
                        fee_multiplier = 1 + self.commission_rate
                        max_shares = int(capital / (actual_buy_price * fee_multiplier * 100)) * 100
                        if max_shares > 0:
                            trade_amount = max_shares * actual_buy_price
                            commission = max(trade_amount * self.commission_rate, self.min_commission)
                            capital -= (trade_amount + commission)
                            holdings += max_shares
                            buy_price = actual_buy_price
                            trade_count += 1
                            trades.append([float(i), 1.0, actual_buy_price, float(max_shares)])

                elif signal == -1 and holdings > 0:
                    if not is_limit_down:
                        actual_sell_price = cur_price * (1 - self.slippage_pct)
                        trade_amount = holdings * actual_sell_price
                        commission = max(trade_amount * self.commission_rate, self.min_commission)
                        tax = trade_amount * self.stamp_duty
                        capital += (trade_amount - commission - tax)
                        trades.append([float(i), -1.0, actual_sell_price, float(holdings)])
                        holdings = 0
                        buy_price = 0.0
                        trade_count += 1

                equity_curve[i] = capital + holdings * cur_price
                if i == n - 1:
                    final_price = cur_price

        self.capital = capital
        self.holdings = holdings
        self.buy_price = buy_price

        return {
            "final_equity": capital + holdings * final_price,
            "trade_count": trade_count,
            "equity_curve": equity_curve,
            "trades": trades
        }
