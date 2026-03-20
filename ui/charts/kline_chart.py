import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
import pandas as pd
from matplotlib.ticker import Formatter, MaxNLocator


class DateFormatter(Formatter):
    def __init__(self, dates):
        self.dates = dates

    def __call__(self, x, pos=None):
        idx = int(round(x))
        if 0 <= idx < len(self.dates):
            return self.dates[idx].strftime('%Y-%m-%d')
        return ''


class KlineChart:
    """纯 matplotlib 打造的高性能专业交互 K 线图"""

    def __init__(self, wrapper=None):
        self.widget_wrapper = wrapper
        self.bg_color = '#1e1e1e'
        self.figure = Figure(figsize=(10, 6), facecolor=self.bg_color)
        self.canvas = FigureCanvas(self.figure)

        self.figure.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.15, hspace=0.08)

        self.ax_main = self.figure.add_subplot(4, 1, (1, 3), facecolor=self.bg_color)
        self.ax_vol = self.figure.add_subplot(4, 1, 4, sharex=self.ax_main, facecolor=self.bg_color)

        self.bg_cache = None
        self.hover_data_map = {}
        self._last_hover_idx = None

        self.v_line = self.ax_main.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)
        self.h_line = self.ax_main.axhline(y=0, color='white', linestyle=':', visible=False, animated=True)
        self.v_line_vol = self.ax_vol.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)

        self.tooltip = self.ax_main.annotate("", xy=(0, 0), xytext=(15, 15), textcoords="offset points",
                                             bbox=dict(boxstyle="round,pad=0.5", fc="#2a2a2a", ec="#555555",
                                                       alpha=0.95),
                                             color="#eeeeee", visible=False, animated=True, zorder=20, fontsize=9)

        self.canvas.mpl_connect("draw_event", self.on_draw_event)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("axes_leave_event", self.on_mouse_leave)
        self._setup_axes()

    def _setup_axes(self):
        for ax in [self.ax_main, self.ax_vol]:
            ax.tick_params(axis='both', colors='#cccccc', labelsize=8)
            for spine in ax.spines.values(): spine.set_color('#333333')
            ax.grid(True, which='major', color='#444444', linestyle='-', linewidth=0.8, alpha=0.5)
            ax.grid(True, which='minor', color='#333333', linestyle='--', linewidth=0.5, alpha=0.3)

        self.ax_main.tick_params(labelbottom=False)
        self.ax_vol.set_ylabel('成交量', color='#cccccc', fontsize=8)

    def on_draw_event(self, event):
        self.bg_cache = self.canvas.copy_from_bbox(self.figure.bbox)

    def draw(self, df):
        self.ax_main.clear()
        self.ax_vol.clear()
        self._setup_axes()
        self.hover_data_map.clear()

        if df is None or df.empty:
            self.ax_main.set_title('K线图 (无数据)', color='#cccccc')
            self.canvas.draw()
            return

        # 1. 均线必须在数据截断前计算！保证前 20 天也能看到完整的均线
        df = df.copy()
        df['MA5'] = df['close'].rolling(5).mean()
        df['MA10'] = df['close'].rolling(10).mean()
        df['MA20'] = df['close'].rolling(20).mean()

        # 2. 限制时间范围：默认显示 100 个交易日
        if len(df) > 100:
            df = df.tail(100).copy()

        dates = df.index.tolist()
        indices = np.arange(len(dates))

        opens, closes = df['open'].values, df['close'].values
        highs, lows = df['high'].values, df['low'].values
        vols = df['volume'].values

        up_color = '#ef5350'  # 柔和明亮的红色（涨）
        down_color = '#26a69a'  # 柔和明亮的青绿色（跌）
        colors = [up_color if c >= o else down_color for c, o in zip(closes, opens)]

        # 3. 缝隙控制：宽度 0.5 留出明显的间隔
        bar_width = 0.5
        body_heights = np.abs(closes - opens)
        self.ax_main.bar(indices, body_heights, bottom=np.minimum(opens, closes),
                         width=bar_width, color=colors, edgecolor=colors, linewidth=1, zorder=3)

        # 处理十字星
        star_indices = np.where(body_heights < 0.001)[0]
        if len(star_indices) > 0:
            star_colors = [colors[i] for i in star_indices]
            self.ax_main.hlines(closes[star_indices], star_indices - (bar_width / 2), star_indices + (bar_width / 2),
                                colors=star_colors, linewidth=1.5, zorder=3)

        # 绘制影线
        self.ax_main.vlines(indices, lows, highs, color=colors, linewidth=1.2, zorder=2)

        # 4. Y 轴自适应修复，避免被压缩成小方块
        y_max = highs.max()
        y_min = lows.min()
        y_margin = (y_max - y_min) * 0.05
        if y_margin == 0: y_margin = y_min * 0.01
        self.ax_main.set_ylim(y_min - y_margin, y_max + y_margin)

        # 成交量
        self.ax_vol.bar(indices, vols, width=bar_width, color=colors, edgecolor=colors, linewidth=1, zorder=3)

        # 绘制均线
        self.ax_main.plot(indices, df['MA5'].values, color='#ff9800', linewidth=1.2, label='MA5')
        self.ax_main.plot(indices, df['MA10'].values, color='#2196f3', linewidth=1.2, label='MA10')
        self.ax_main.plot(indices, df['MA20'].values, color='#e91e63', linewidth=1.2, label='MA20')
        self.ax_main.legend(loc='upper left', frameon=False, labelcolor='#cccccc', fontsize=9)

        # 坐标轴与留白优化
        self.ax_vol.xaxis.set_major_locator(MaxNLocator(8))
        self.ax_vol.xaxis.set_major_formatter(DateFormatter(dates))
        self.ax_main.set_xlim(-1, len(dates) + 3)  # 右侧留出一定空间

        for i, d in enumerate(dates):
            self.hover_data_map[i] = {
                'date': d.strftime('%Y-%m-%d'),
                'open': opens[i], 'close': closes[i],
                'high': highs[i], 'low': lows[i], 'vol': vols[i]
            }

        self.v_line = self.ax_main.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)
        self.h_line = self.ax_main.axhline(y=0, color='white', linestyle=':', visible=False, animated=True)
        self.v_line_vol = self.ax_vol.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)
        self.tooltip = self.ax_main.annotate("", xy=(0, 0), xytext=(15, 15), textcoords="offset points",
                                             bbox=dict(boxstyle="round,pad=0.4", fc="#2a2a2a", ec="#666666", alpha=0.9),
                                             color="#eeeeee", visible=False, animated=True, zorder=20, fontsize=9)

        self.canvas.draw()

    def on_mouse_move(self, event):
        if not event.inaxes or not self.bg_cache: return
        x_idx = int(round(event.xdata))
        if x_idx not in self.hover_data_map or x_idx == self._last_hover_idx: return
        self._last_hover_idx = x_idx
        p = self.hover_data_map[x_idx]

        self.v_line.set_xdata([x_idx, x_idx])
        self.v_line_vol.set_xdata([x_idx, x_idx])
        self.h_line.set_ydata([p['close'], p['close']])

        text = f"{p['date']}\n开盘: {p['open']:.2f}\n收盘: {p['close']:.2f}\n最高: {p['high']:.2f}\n最低: {p['low']:.2f}\n成交量: {p['vol']:,.0f}"
        self.tooltip.set_text(text)
        y_pos = event.ydata if event.inaxes == self.ax_main else p['close']
        self.tooltip.xy = (x_idx, y_pos)

        self.canvas.restore_region(self.bg_cache)
        for art in [self.v_line, self.h_line, self.v_line_vol, self.tooltip]:
            art.set_visible(True)
            if art == self.v_line_vol:
                self.ax_vol.draw_artist(art)
            else:
                self.ax_main.draw_artist(art)
        self.canvas.blit(self.figure.bbox)

    def on_mouse_leave(self, event):
        if self.bg_cache:
            self.canvas.restore_region(self.bg_cache)
            self.canvas.blit(self.figure.bbox)
        self._last_hover_idx = None