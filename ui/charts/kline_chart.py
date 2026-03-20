import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import mplfinance as mpf
import pandas as pd

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

class KlineChart:
    def __init__(self):
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        self.ax_main = self.figure.add_subplot(2, 1, 1)
        self.ax_vol = self.figure.add_subplot(2, 1, 2, sharex=self.ax_main)
        self.ax_main.set_ylabel('价格 (元)')
        self.ax_main.grid(True, linestyle=':', alpha=0.5)
        self.ax_vol.set_ylabel('成交量 (手)')
        self.ax_vol.grid(True, linestyle=':', alpha=0.5)
        self.figure.tight_layout()
        self.df = None
        self.draw_placeholder()

    def draw_placeholder(self):
        self.ax_main.set_title('K线图 (无数据)')
        self.ax_main.clear()
        self.ax_vol.clear()
        self.canvas.draw()

    def draw(self, df):
        if df.empty:
            self.draw_placeholder()
            return
        if len(df) > 500:
            df = df.tail(500).copy()
        # 确保索引是 DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        self.df = df
        self.ax_main.clear()
        self.ax_vol.clear()

        # 计算均线
        df_plot = df.copy()
        df_plot['MA5'] = df_plot['close'].rolling(window=5).mean()
        df_plot['MA10'] = df_plot['close'].rolling(window=10).mean()
        df_plot['MA20'] = df_plot['close'].rolling(window=20).mean()
        df_plot['MA60'] = df_plot['close'].rolling(window=60).mean()

        style = mpf.make_mpf_style(
            base_mpf_style='charles',
            rc={'font.family': 'sans-serif',
                'font.sans-serif': ['SimHei', 'Microsoft YaHei']}
        )

        # 添加均线到主图
        ap = [
            mpf.make_addplot(df_plot['MA5'], ax=self.ax_main, color='blue', width=0.8, label='MA5'),
            mpf.make_addplot(df_plot['MA10'], ax=self.ax_main, color='orange', width=0.8, label='MA10'),
            mpf.make_addplot(df_plot['MA20'], ax=self.ax_main, color='green', width=0.8, label='MA20'),
            mpf.make_addplot(df_plot['MA60'], ax=self.ax_main, color='purple', width=0.8, label='MA60'),
        ]

        mpf.plot(
            df_plot,
            type='candle',
            volume=self.ax_vol,
            style=style,
            ax=self.ax_main,
            addplot=ap,
            xrotation=45,
            warn_too_much_data=10000,
            figscale=1.0
        )

        # 添加图例
        self.ax_main.legend(loc='upper left')
        self.figure.tight_layout()
        self.canvas.draw()

    def get_canvas(self):
        return self.canvas