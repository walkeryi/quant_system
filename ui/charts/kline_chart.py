# quant_system/ui/charts/kline_chart.py
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
        self.current_period = 'daily'

        # --- 交互状态 ---
        self.tooltip_visible = False  # 双击切换
        self._is_dragging = False
        self.tooltip_pos = [0.02, 0.96]  # 初始位置
        self._drag_offset = (0, 0)

        # 绑定事件
        self.canvas.mpl_connect("draw_event", self.on_draw_event)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("axes_leave_event", self.on_mouse_leave)
        self.canvas.mpl_connect("button_press_event", self.on_mouse_press)
        self.canvas.mpl_connect("button_release_event", self.on_mouse_release)

        self._init_cursor_artists()
        self._setup_axes()

    def _init_cursor_artists(self):
        self.v_line = self.ax_main.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)
        self.h_line = self.ax_main.axhline(y=0, color='white', linestyle=':', visible=False, animated=True)
        self.v_line_vol = self.ax_vol.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)

        self.tooltip = self.ax_main.annotate(
            "", xy=tuple(self.tooltip_pos), xycoords="axes fraction",
            bbox=dict(boxstyle="round,pad=0.5", fc="#2a2a2a", ec="#666666", alpha=0.95),
            color="#eeeeee", visible=False, animated=True, zorder=100, fontsize=10,
            va='top', ha='left'
        )

    def on_draw_event(self, event):
        self.bg_cache = self.canvas.copy_from_bbox(self.figure.bbox)

    def on_mouse_press(self, event):
        if event.button != 1: return
        if event.dblclick:
            self.tooltip_visible = not self.tooltip_visible
            self._do_blit()
            return
        if self.tooltip_visible:
            inv = self.ax_main.transAxes.inverted()
            mx, my = inv.transform((event.x, event.y))
            tx, ty = self.tooltip_pos
            # 判定是否抓住信息牌
            if tx <= mx <= tx + 0.3 and ty - 0.5 <= my <= ty:
                self._is_dragging = True
                self._drag_offset = (mx - tx, my - ty)

    def on_mouse_release(self, event):
        self._is_dragging = False

    def on_mouse_move(self, event):
        if not self.bg_cache: return
        inv = self.ax_main.transAxes.inverted()
        mx, my = inv.transform((event.x, event.y))

        if self._is_dragging:
            self.tooltip_pos = [np.clip(mx - self._drag_offset[0], 0, 0.7),
                                np.clip(my - self._drag_offset[1], 0.4, 1.0)]
            self.tooltip.xy = tuple(self.tooltip_pos)
            self._do_blit();
            return

        if not event.inaxes: return
        x_idx = int(round(event.xdata))
        if x_idx not in self.hover_data_map or x_idx == self._last_hover_idx: return

        self._last_hover_idx = x_idx
        p = self.hover_data_map[x_idx]

        self.v_line.set_xdata([x_idx, x_idx])
        self.h_line.set_ydata([p['close'], p['close']])

        # 信息牌字段补全
        text = (f"【{self.current_period}】 {p['date']}\n"
                f"───────\n"
                f"开盘: {p['open']:.2f}\n"
                f"最高: {p['high']:.2f}\n"
                f"最低: {p['low']:.2f}\n"
                f"收盘: {p['close']:.2f}\n"
                f"涨跌: {p['pct_chg']:+.2f}%\n"
                f"成交: {p['vol']:,.0f}手\n"
                f"金额: {p['amount']:,.0f}元")
        self.tooltip.set_text(text)
        self.tooltip.xy = tuple(self.tooltip_pos)
        self._do_blit()

    def _do_blit(self):
        try:
            self.canvas.restore_region(self.bg_cache)
            for art in [self.v_line, self.h_line]:
                art.set_visible(True);
                self.ax_main.draw_artist(art)
            if self.tooltip_visible:
                self.tooltip.set_visible(True);
                self.ax_main.draw_artist(self.tooltip)
            else:
                self.tooltip.set_visible(False)
            self.canvas.blit(self.figure.bbox)
        except:
            pass

    def _setup_axes(self):
        for ax in [self.ax_main, self.ax_vol]:
            ax.tick_params(colors='#cccccc', labelsize=8)
            ax.grid(True, color='#444444', alpha=0.5)

    def draw(self, df, period='daily'):
        self.current_period = period
        self.ax_main.clear();
        self.ax_vol.clear();
        self._setup_axes()
        if df is None or df.empty: self.canvas.draw(); return

        df = df.copy()
        df['pct_chg'] = df['close'].pct_change().fillna(0) * 100
        df = df.tail(500)

        indices = np.arange(len(df))
        colors = ['#ff3333' if c >= o else '#00e676' for c, o in zip(df['close'], df['open'])]

        self.ax_main.add_collection(
            LineCollection([((i, l), (i, h)) for i, l, h in zip(indices, df['low'], df['high'])], colors=colors,
                           linewidths=1.2))
        self.ax_main.add_collection(PolyCollection(
            [((i - 0.3, o), (i - 0.3, c), (i + 0.3, c), (i + 0.3, o)) for i, o, c in
             zip(indices, df['open'], df['close'])], facecolors=colors, edgecolors=colors))

        self.ax_main.set_ylim(df['low'].min() * 0.98, df['high'].max() * 1.02)
        self.ax_main.set_xlim(-1, len(df) + 2)

        self.ax_vol.add_collection(PolyCollection(
            [((i - 0.3, 0), (i - 0.3, v), (i + 0.3, v), (i + 0.3, 0)) for i, v in zip(indices, df['volume'])],
            facecolors=colors, edgecolors=colors))
        self.ax_vol.set_ylim(0, df['volume'].max() * 1.1)
        self.ax_vol.xaxis.set_major_formatter(DateFormatter(df.index))

        for i, (d, row) in enumerate(df.iterrows()):
            self.hover_data_map[i] = {
                'date': d.strftime('%Y-%m-%d'), 'open': row['open'], 'high': row['high'],
                'low': row['low'], 'close': row['close'], 'vol': row['volume'],
                'amount': row.get('amount', 0), 'pct_chg': row['pct_chg']
            }
        self._init_cursor_artists();
        self.canvas.draw()

    def on_mouse_leave(self, event):
        if self.bg_cache: self.canvas.restore_region(self.bg_cache); self.canvas.blit(self.figure.bbox)
        self._last_hover_idx = None;
        self._is_dragging = False