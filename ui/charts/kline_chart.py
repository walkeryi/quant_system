import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
import pandas as pd
from matplotlib.ticker import Formatter, MaxNLocator
from matplotlib.collections import PolyCollection, LineCollection


class DateFormatter(Formatter):
    def __init__(self, dates):
        self.dates = dates

    def __call__(self, x, pos=None):
        idx = int(round(x))
        if 0 <= idx < len(self.dates):
            return self.dates[idx].strftime('%Y-%m-%d')
        return ''


class KlineChart:
    """纯 matplotlib 打造的高性能专业交互 K 线图（支持日线/周线动态光标）"""

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
        self.current_period = 'daily'  # 默认日线

        self.canvas.mpl_connect("draw_event", self.on_draw_event)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("axes_leave_event", self.on_mouse_leave)

        # 初次初始化光标组件
        self._init_cursor_artists()
        self._setup_axes()

    def _init_cursor_artists(self):
        """初始化/重建 十字光标和弹窗组件（必须 animated=True 供局部刷新）"""
        self.v_line = self.ax_main.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)
        self.h_line = self.ax_main.axhline(y=0, color='white', linestyle=':', visible=False, animated=True)
        self.v_line_vol = self.ax_vol.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)
        self.tooltip = self.ax_main.annotate("", xy=(0, 0), xytext=(15, 15), textcoords="offset points",
                                             bbox=dict(boxstyle="round,pad=0.4", fc="#2a2a2a", ec="#666666",
                                                       alpha=0.95),
                                             color="#eeeeee", visible=False, animated=True, zorder=20, fontsize=9)

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

    def draw(self, df, period='daily'):
        self.current_period = period
        self.ax_main.clear()
        self.ax_vol.clear()
        self._setup_axes()
        self.hover_data_map.clear()
        self._last_hover_idx = None

        if df is None or df.empty:
            p_name = "日" if period == 'daily' else "周" if period == 'weekly' else "月"
            self.ax_main.set_title(f'{p_name}K线图 (无数据)', color='#cccccc')
            self.canvas.draw()
            return

        df = df.copy()
        df['MA5'] = df['close'].rolling(5).mean()
        df['MA10'] = df['close'].rolling(10).mean()
        df['MA20'] = df['close'].rolling(20).mean()

        if len(df) > 500:
            df = df.tail(500).copy()

        dates = df.index.tolist()
        indices = np.arange(len(dates))

        opens, closes = df['open'].values, df['close'].values
        highs, lows = df['high'].values, df['low'].values
        vols = df['volume'].values

        up_color, down_color = '#ef5350', '#26a69a'
        colors = [up_color if c >= o else down_color for c, o in zip(closes, opens)]
        bar_width = 0.6

        # ================= 渲染性能革命：Collection 机制 =================

        segments = [((i, low), (i, high)) for i, low, high in zip(indices, lows, highs)]
        lines = LineCollection(segments, colors=colors, linewidths=1.2, zorder=2)
        self.ax_main.add_collection(lines)

        verts = []
        for i, o, c in zip(indices, opens, closes):
            if abs(c - o) < 0.001:
                c = o + 0.001
            left, right = i - bar_width / 2, i + bar_width / 2
            verts.append(((left, o), (left, c), (right, c), (right, o)))

        bodies = PolyCollection(verts, facecolors=colors, edgecolors=colors, linewidths=1, zorder=3)
        self.ax_main.add_collection(bodies)

        y_max, y_min = highs.max(), lows.min()
        y_margin = (y_max - y_min) * 0.05 if y_max != y_min else y_min * 0.01
        self.ax_main.set_ylim(y_min - y_margin, y_max + y_margin)
        self.ax_main.set_xlim(-1, len(dates) + 3)

        vol_verts = []
        for i, v in zip(indices, vols):
            left, right = i - bar_width / 2, i + bar_width / 2
            vol_verts.append(((left, 0), (left, v), (right, v), (right, 0)))
        vol_bodies = PolyCollection(vol_verts, facecolors=colors, edgecolors=colors, linewidths=1, zorder=3)
        self.ax_vol.add_collection(vol_bodies)

        v_max = vols.max()
        self.ax_vol.set_ylim(0, v_max * 1.05 if v_max > 0 else 1)

        # 均线
        self.ax_main.plot(indices, df['MA5'].values, color='#ff9800', linewidth=1.2, label='MA5')
        self.ax_main.plot(indices, df['MA10'].values, color='#2196f3', linewidth=1.2, label='MA10')
        self.ax_main.plot(indices, df['MA20'].values, color='#e91e63', linewidth=1.2, label='MA20')
        self.ax_main.legend(loc='upper left', frameon=False, labelcolor='#cccccc', fontsize=9)

        self.ax_vol.xaxis.set_major_locator(MaxNLocator(8))
        self.ax_vol.xaxis.set_major_formatter(DateFormatter(dates))

        for i, d in enumerate(dates):
            self.hover_data_map[i] = {
                'date': d.strftime('%Y-%m-%d'),
                'open': opens[i], 'close': closes[i],
                'high': highs[i], 'low': lows[i], 'vol': vols[i]
            }

        self._init_cursor_artists()
        self.canvas.draw()

    def on_mouse_move(self, event):
        if not event.inaxes or not self.bg_cache: return

        # ================= 终极防闪退防御机制 =================
        # 当网络请求失败时，外部的 stock_tab.py 会强行调用 ax.clear() 来绘制红色报错文字。
        # 这会导致底层的十字光标和 Tooltip 被无情剥离画布 (axes 变成 None)。
        # 如果此时鼠标还在图表上滑动，必须强制拦截并清空悬浮记录，否则会触发 transData 报错！
        if getattr(self, 'tooltip', None) is None or getattr(self.tooltip, 'axes', None) is None:
            self.hover_data_map.clear()
            self._last_hover_idx = None
            return
        # ====================================================

        x_idx = int(round(event.xdata))
        if x_idx not in self.hover_data_map or x_idx == self._last_hover_idx: return
        self._last_hover_idx = x_idx
        p = self.hover_data_map[x_idx]

        self.v_line.set_xdata([x_idx, x_idx])
        self.v_line_vol.set_xdata([x_idx, x_idx])
        self.h_line.set_ydata([p['close'], p['close']])

        # 动态提示词
        period_str = "日线" if self.current_period == 'daily' else "周线" if self.current_period == 'weekly' else "月线"
        text = (f"【{period_str}】 {p['date']}\n开盘: {p['open']:.2f}\n收盘: {p['close']:.2f}\n"
                f"最高: {p['high']:.2f}\n最低: {p['low']:.2f}\n成交量: {p['vol']:,.0f}")
        self.tooltip.set_text(text)

        y_pos = event.ydata if event.inaxes == self.ax_main else p['close']
        self.tooltip.xy = (x_idx, y_pos)

        try:
            self.canvas.restore_region(self.bg_cache)
            # 加强了对光标组件状态的判断，确保没被外部摧毁才去渲染
            for art in [self.v_line, self.h_line, self.v_line_vol, self.tooltip]:
                if getattr(art, 'axes', None) is not None:
                    art.set_visible(True)
                    if art == self.v_line_vol:
                        self.ax_vol.draw_artist(art)
                    else:
                        self.ax_main.draw_artist(art)
            self.canvas.blit(self.figure.bbox)
        except Exception:
            # 遭遇极端未知图层销毁状态时，不抛错，静默吸收
            pass

    def on_mouse_leave(self, event):
        try:
            if self.bg_cache:
                self.canvas.restore_region(self.bg_cache)
                self.canvas.blit(self.figure.bbox)
        except Exception:
            pass
        self._last_hover_idx = None