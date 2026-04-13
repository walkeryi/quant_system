# 文件路径: quant_system/backtest_core.py

class BacktestEngine:
    """
    纯 Python 版的高性能回测引擎（替代原有的 C++ pyd）
    彻底解决 Python 3.14 / Pybind11 / 虚拟环境交错导致的闪退问题
    """

    def __init__(self, initial_capital: float):
        self.capital = float(initial_capital)
        self.holdings = 0
        self.buy_price = 0.0

    def run(self, prices, signals, stop_loss_pct):
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

                # 止损逻辑
                if holdings > 0 and stop_loss_pct > 0:
                    if (cur_price - buy_price) / buy_price * 100.0 <= -stop_loss_pct:
                        signal = -1

                # 买入逻辑
                if signal == 1 and capital >= cur_price * 100:
                    shares = int(capital / (cur_price * 100)) * 100
                    if shares > 0:
                        capital -= shares * cur_price
                        holdings += shares
                        buy_price = cur_price
                        trade_count += 1
                        # 记录：[索引, 买卖方向(1买-1卖), 价格, 数量]
                        trades.append([float(i), 1.0, cur_price, float(shares)])

                # 卖出逻辑
                elif signal == -1 and holdings > 0:
                    capital += holdings * cur_price
                    trades.append([float(i), -1.0, cur_price, float(holdings)])
                    holdings = 0
                    buy_price = 0.0
                    trade_count += 1

                # 记录每日权益
                equity_curve[i] = capital + holdings * cur_price
                if i == n - 1:
                    final_price = cur_price

        # 保存状态
        self.capital = capital
        self.holdings = holdings
        self.buy_price = buy_price

        return {
            "final_equity": capital + holdings * final_price,
            "trade_count": trade_count,
            "equity_curve": equity_curve,
            "trades": trades
        }