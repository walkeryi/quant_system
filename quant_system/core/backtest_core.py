# -*- coding: utf-8 -*-
# 文件路径: quant_system/core/backtest_core.py

class BacktestEngine:
    """
    纯 Python 版的高性能回测引擎 V3.0
    新增特征：涨跌停无法成交限制 (Limit Up/Down Constraint)
    """

    def __init__(self, initial_capital: float):
        self.capital = float(initial_capital)
        self.holdings = 0
        self.buy_price = 0.0
        
        # === 真实交易成本设定 ===
        self.commission_rate = 0.00025  # 券商佣金 (万2.5，双向)
        self.stamp_duty = 0.0005        # 印花税 (万5，仅卖出收取)
        self.slippage_pct = 0.001       # 滑点比例 (千分之1，模拟成交价劣势)
        self.min_commission = 5.0       # 最低佣金 5 元

    def run(self, prices, signals, limit_ups, limit_downs, stop_loss_pct):
        """
        :param limit_ups: 布尔数组，标记每日是否涨停
        :param limit_downs: 布尔数组，标记每日是否跌停
        """
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
                is_limit_up = bool(limit_ups[i])
                is_limit_down = bool(limit_downs[i])

                # 1. 止损逻辑判断
                if holdings > 0 and stop_loss_pct > 0:
                    if (cur_price - buy_price) / buy_price * 100.0 <= -stop_loss_pct:
                        signal = -1  # 触发强制止损信号

                # 2. 买入逻辑 (包含滑点与佣金，受涨停限制)
                if signal == 1 and holdings == 0:
                    if is_limit_up:
                        # 涨停板封死，买单无效（废单）
                        pass 
                    else:
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

                # 3. 卖出逻辑 (包含滑点、佣金与印花税，受跌停限制)
                elif signal == -1 and holdings > 0:
                    if is_limit_down:
                        # 跌停板封死，卖单无法成交（被关在里面）
                        pass
                    else:
                        actual_sell_price = cur_price * (1 - self.slippage_pct)
                        trade_amount = holdings * actual_sell_price
                        
                        commission = max(trade_amount * self.commission_rate, self.min_commission)
                        tax = trade_amount * self.stamp_duty
                        
                        capital += (trade_amount - commission - tax)
                        trades.append([float(i), -1.0, actual_sell_price, float(holdings)])
                        
                        holdings = 0
                        buy_price = 0.0
                        trade_count += 1

                # 4. 记录每日权益
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
