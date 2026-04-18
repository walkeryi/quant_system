# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from matplotlib.ticker import MultipleLocator

class FenshiVolumeChart:
    def __init__(self):
        self.bg_color = '#1e1e1e'
        self.figure = Figure(figsize=(10, 2), facecolor=self.bg_color)
        self.canvas = FigureCanvas(self.figure)
        # 【修复】：right 设为 0.92 对齐价格图, top 必须大于 bottom
        self.figure.subplots_adjust(left=0.08, right=0.92, top=0.95, bottom=0.25)
        self.ax = self.figure.add_subplot(111, facecolor=self.bg_color)

        self.hover_data_map = {};
        self.bg_cache = None
        self.v_line = self.ax.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)
        self.canvas.mpl_connect("draw_event", self.on_draw_event)
        self._setup_axes()

    def on_draw_event(self, event):
        self.bg_cache = self.canvas.copy_from_bbox(self.figure.bbox)

    def _setup_axes(self):
        self.ax.tick_params(axis='y', colors='#cccccc', labelsize=8)
        self.ax.set_xlim(0, 240);
        self.ax.set_xticks([0, 30, 60, 90, 120, 150, 180, 210, 240]);
        self.ax.set_xticklabels([])

        # --- 新增：大格与小格刻度网格（与上方价格图对齐） ---
        self.ax.xaxis.set_minor_locator(MultipleLocator(15))
        self.ax.grid(True, which='major', axis='x', color='#444444', linestyle='-', linewidth=0.8)
        self.ax.grid(True, which='minor', axis='x', color='#333333', linestyle='--', linewidth=0.5)

    def draw(self, df):
        self.ax.clear();
        self._setup_axes();
        self.hover_data_map.clear()
        if df.empty or 'minute_volume' not in df.columns: return self.canvas.draw()

        indices = []
        for t in df['time']:
            h, m = map(int, t.split(':'))
            idx = (h * 60 + m - 570) if h * 60 + m <= 690 else (h * 60 + m - 780 + 120)
            if 0 <= idx <= 240: indices.append(idx)

        # 【应用 API 增量成交量】
        vols = df['minute_volume'].values[:len(indices)]
        prices = df['price'].values[:len(indices)]
        zuoshou = df.attrs.get('base', {}).get('ZuoShou', prices[0])

        # 【颜色逻辑】：当前价 >= 前一分钟价则为红，否则为绿
        colors = []
        for i in range(len(prices)):
            ref_price = prices[i - 1] if i > 0 else zuoshou
            colors.append('#ff4444' if prices[i] >= ref_price else '#00c853')

        self.ax.bar(indices, vols, width=0.8, color=colors, zorder=5)
        self.ax.set_ylim(0, max(vols) * 1.1 if len(vols) > 0 else 100)

        for i, idx in enumerate(indices): self.hover_data_map[idx] = {'time': df.iloc[i]['time']}
        self.v_line = self.ax.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)
        self.canvas.draw()

    def update_crosshair_sync(self, x_idx):
        if not self.bg_cache: return
        self.canvas.restore_region(self.bg_cache)
        if x_idx in self.hover_data_map:
            self.v_line.set_xdata([x_idx, x_idx]);
            self.v_line.set_visible(True)
            self.ax.draw_artist(self.v_line)
        self.canvas.blit(self.figure.bbox)

    def hide_crosshair(self):
        if self.bg_cache: self.canvas.restore_region(self.bg_cache); self.canvas.blit(self.figure.bbox)