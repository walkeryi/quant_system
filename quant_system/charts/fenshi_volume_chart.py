# -*- coding: utf-8 -*-
"""
分时成交量图
"""
import logging
import time
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
matplotlib.rcParams['axes.unicode_minus'] = False
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from matplotlib.ticker import MultipleLocator

logger = logging.getLogger('quant_system')


class FenshiVolumeChart:
    def __init__(self):
        self.bg_color = '#1e1e1e'
        self.figure = Figure(figsize=(10, 2), facecolor=self.bg_color)
        self.canvas = FigureCanvas(self.figure)
        self.figure.subplots_adjust(left=0.08, right=0.92, top=0.95, bottom=0.25)
        self.ax = self.figure.add_subplot(111, facecolor=self.bg_color)
        self.hover_data_map = {}
        self.bg_cache = None
        self.v_line = self.ax.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)
        self.canvas.mpl_connect("draw_event", self.on_draw_event)
        self._setup_axes()

    def on_draw_event(self, event):
        self.bg_cache = self.canvas.copy_from_bbox(self.figure.bbox)

    def _setup_axes(self):
        self.ax.tick_params(axis='y', colors='#cccccc', labelsize=8)
        self.ax.set_xlim(0, 240)
        self.ax.set_xticks([0, 30, 60, 90, 120, 150, 180, 210, 240])
        self.ax.set_xticklabels([])
        self.ax.xaxis.set_minor_locator(MultipleLocator(15))
        self.ax.grid(True, which='major', axis='x', color='#444444', linestyle='-', linewidth=0.8)
        self.ax.grid(True, which='minor', axis='x', color='#333333', linestyle='--', linewidth=0.5)

    def draw(self, df):
        t0 = time.perf_counter()
        self.ax.clear()
        self._setup_axes()
        self.hover_data_map.clear()
        if df.empty or 'minute_volume' not in df.columns:
            return self.canvas.draw()

        times = df['time'].values
        vols = df['minute_volume'].values
        prices = df['price'].values

        n = len(times)
        indices = np.empty(n, dtype=int)
        for i in range(n):
            h, m = int(times[i][:2]), int(times[i][3:])
            total = h * 60 + m
            indices[i] = total - 570 if total <= 690 else total - 780 + 120

        mask = (indices >= 0) & (indices <= 240)
        indices = indices[mask]
        vols = vols[mask]
        prices = prices[mask]

        zuoshou = float(df.attrs.get('base', {}).get('ZuoShou', 0)) / 1000.0
        if zuoshou == 0 and len(prices) > 0:
            zuoshou = prices[0]

        prev_prices = np.roll(prices, 1)
        prev_prices[0] = zuoshou
        bar_colors = np.where(prices >= prev_prices, '#ff4444', '#00c853')

        self.ax.bar(indices, vols, width=0.8, color=bar_colors, zorder=5)
        max_vol = vols.max()
        self.ax.set_ylim(0, max_vol * 1.1 if max_vol > 0 else 100)

        for i, idx in enumerate(indices):
            self.hover_data_map[int(idx)] = {'time': str(df['time'].values[mask][i])}
        self.v_line = self.ax.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)

        t1 = time.perf_counter()
        self.canvas.draw()
        t2 = time.perf_counter()
        logger.info(f"[VolumeChart] 绘图完成: 数据处理={(t1-t0)*1000:.1f}ms canvas.draw()={(t2-t1)*1000:.1f}ms 总计={(t2-t0)*1000:.1f}ms")

    def update_crosshair_sync(self, x_idx):
        if not self.bg_cache:
            return
        self.canvas.restore_region(self.bg_cache)
        if x_idx in self.hover_data_map:
            self.v_line.set_xdata([x_idx, x_idx])
            self.v_line.set_visible(True)
            self.ax.draw_artist(self.v_line)
        self.canvas.blit(self.figure.bbox)

    def hide_crosshair(self):
        if self.bg_cache:
            self.canvas.restore_region(self.bg_cache)
            self.canvas.blit(self.figure.bbox)
