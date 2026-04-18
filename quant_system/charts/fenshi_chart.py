# -*- coding: utf-8 -*-
"""
分时图组件
"""
import logging
import time
import matplotlib
matplotlib.use('qtagg')
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
matplotlib.rcParams['axes.unicode_minus'] = False
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import numpy as np

logger = logging.getLogger('quant_system')


class FenshiChart:
    """专业分时图：支持双击开关信息牌、单击自由拖拽"""

    def __init__(self, wrapper=None):
        self.widget_wrapper = wrapper
        self.bg_color = '#1e1e1e'
        self.zuoshou = 0
        self.bg_cache = None
        self._last_hover_idx = None
        self.hover_data_map = {}
        self.tooltip_visible = False
        self._is_dragging = False
        self.tooltip_pos = [0.02, 0.96]
        self._drag_offset = (0, 0)

        self.figure = Figure(figsize=(10, 6), facecolor=self.bg_color)
        self.canvas = FigureCanvas(self.figure)
        self.figure.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.1)
        self.ax_price = self.figure.add_subplot(111, facecolor=self.bg_color)
        self.ax_pct = self.ax_price.twinx()

        self._init_cursor_artists()
        self.canvas.mpl_connect("draw_event", self.on_draw_event)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("axes_leave_event", self.on_mouse_leave)
        self.canvas.mpl_connect("button_press_event", self.on_mouse_press)
        self.canvas.mpl_connect("button_release_event", self.on_mouse_release)
        self._setup_axes()

    def _init_cursor_artists(self):
        self.v_line = self.ax_price.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)
        self.h_line = self.ax_price.axhline(y=0, color='white', linestyle=':', visible=False, animated=True)
        self.tooltip = self.ax_price.annotate(
            "", xy=tuple(self.tooltip_pos), xycoords="axes fraction",
            bbox=dict(boxstyle="round,pad=0.5", fc="#2a2a2a", ec="#666666", alpha=0.95),
            color="#eeeeee", visible=False, animated=True, zorder=100, fontsize=10,
            va='top', ha='left'
        )
        self.hline_zuoshou = self.ax_price.axhline(y=0, color='#444444', linewidth=2, zorder=3, visible=False)

    def on_draw_event(self, event):
        self.bg_cache = self.canvas.copy_from_bbox(self.figure.bbox)

    def on_mouse_press(self, event):
        if event.button != 1:
            return
        if event.dblclick:
            self.tooltip_visible = not self.tooltip_visible
            self._do_blit()
            return
        if self.tooltip_visible:
            inv = self.ax_price.transAxes.inverted()
            mx, my = inv.transform((event.x, event.y))
            tx, ty = self.tooltip_pos
            if tx <= mx <= tx + 0.35 and ty - 0.55 <= my <= ty:
                self._is_dragging = True
                self._drag_offset = (mx - tx, my - ty)

    def on_mouse_release(self, event):
        self._is_dragging = False

    def on_mouse_move(self, event):
        if not self.bg_cache:
            return
        inv = self.ax_price.transAxes.inverted()
        mx, my = inv.transform((event.x, event.y))

        if self._is_dragging:
            new_x = np.clip(mx - self._drag_offset[0], 0, 0.65)
            new_y = np.clip(my - self._drag_offset[1], 0.55, 1.0)
            self.tooltip_pos = [new_x, new_y]
            self.tooltip.xy = tuple(self.tooltip_pos)
            self._do_blit()
            return

        if not event.inaxes:
            return
        x_idx = int(round(event.xdata))
        if x_idx not in self.hover_data_map or x_idx == self._last_hover_idx:
            return

        self._last_hover_idx = x_idx
        p = self.hover_data_map[x_idx]
        self.v_line.set_xdata([x_idx, x_idx])
        self.h_line.set_ydata([p['price'], p['price']])

        text = (f"时间: {p['time']}\n"
                f"───────\n"
                f"价格: {p['price']:.2f}\n"
                f"涨幅: {p['pct_chg']:+.2f}%\n"
                f"均价: {p['avg_price']:.2f}\n"
                f"成交: {p['vol']:,.0f}手\n"
                f"换手: {p['huan_shou']:.2f}%\n"
                f"量比: {p['liang_bi']:.2f}\n"
                f"委比: {p['wei_bi']:+.2f}%\n"
                f"内盘: {p['nei_pan']:,.0f}手\n"
                f"外盘: {p['wai_pan']:,.0f}手")

        self.tooltip.set_text(text)
        self.tooltip.xy = tuple(self.tooltip_pos)
        self._do_blit()

        if self.widget_wrapper:
            self.widget_wrapper.crosshairSyncSignal.emit(x_idx)

    def _do_blit(self):
        try:
            self.canvas.restore_region(self.bg_cache)
            for art in [self.v_line, self.h_line]:
                art.set_visible(True)
                self.ax_price.draw_artist(art)
            if self.tooltip_visible:
                self.tooltip.set_visible(True)
                self.ax_price.draw_artist(self.tooltip)
            else:
                self.tooltip.set_visible(False)
            self.canvas.blit(self.figure.bbox)
        except:
            pass

    def _setup_axes(self):
        self.ax_price.set_xlim(0, 240)
        self.ax_price.set_xticks([0, 60, 120, 180, 240])
        self.ax_price.set_xticklabels(["09:30", "10:30", "11:30/13:00", "14:00", "15:00"], color='#cccccc', fontsize=8)
        self.ax_price.grid(True, which='both', color='#333333', linestyle='--', alpha=0.5)

    def draw(self, df, base):
        t0 = time.perf_counter()
        if df.empty:
            return

        for line in self.ax_price.lines:
            if line not in [self.v_line, self.h_line, self.hline_zuoshou]:
                line.remove()
        self.hover_data_map = {}

        time_col = df['time'].values
        price_col = df['price'].values
        avg_col = df['avg_price'].values if 'avg_price' in df.columns else None
        pct_col = df['pct_chg'].values if 'pct_chg' in df.columns else None
        vol_col = df['minute_volume'].values if 'minute_volume' in df.columns else None
        hs_col = df['huan_shou'].values if 'huan_shou' in df.columns else None
        lb_col = df['liang_bi'].values if 'liang_bi' in df.columns else None
        wb_col = df['wei_bi'].values if 'wei_bi' in df.columns else None
        np_col = df['nei_pan'].values if 'nei_pan' in df.columns else None
        wp_col = df['wai_pan'].values if 'wai_pan' in df.columns else None

        n = len(time_col)
        indices = np.empty(n, dtype=int)
        for i in range(n):
            parts = str(time_col[i]).split(':')
            h, m = int(parts[0]), int(parts[1])
            total = h * 60 + m
            indices[i] = total - 570 if total <= 690 else total - 780 + 120

        mask = (indices >= 0) & (indices <= 240)
        indices = indices[mask]
        prices = price_col[mask]
        avgs = avg_col[mask] if avg_col is not None else np.zeros(mask.sum())
        for i, idx in enumerate(indices):
            self.hover_data_map[int(idx)] = {
                'time': str(time_col[mask][i]),
                'price': float(prices[i]),
                'avg_price': float(avgs[i]) if not np.isnan(avgs[i]) else 0.0,
                'pct_chg': float(pct_col[mask][i]) if pct_col is not None and not np.isnan(pct_col[mask][i]) else 0.0,
                'vol': float(vol_col[mask][i]) if vol_col is not None and not np.isnan(vol_col[mask][i]) else 0.0,
                'huan_shou': float(hs_col[mask][i]) if hs_col is not None and not np.isnan(hs_col[mask][i]) else 0.0,
                'liang_bi': float(lb_col[mask][i]) if lb_col is not None and not np.isnan(lb_col[mask][i]) else 0.0,
                'wei_bi': float(wb_col[mask][i]) if wb_col is not None and not np.isnan(wb_col[mask][i]) else 0.0,
                'nei_pan': float(np_col[mask][i]) if np_col is not None and not np.isnan(np_col[mask][i]) else 0.0,
                'wai_pan': float(wp_col[mask][i]) if wp_col is not None and not np.isnan(wp_col[mask][i]) else 0.0,
            }

        self.zuoshou = float(base.get('ZuoShou', 0)) / 1000.0

        if len(prices) == 0:
            if self.zuoshou == 0:
                return
            diff = self.zuoshou * 0.02
        else:
            if self.zuoshou == 0:
                self.zuoshou = float(prices[0])
            diff = max(abs(float(prices.max()) - self.zuoshou), abs(self.zuoshou - float(prices.min()))) * 1.1

        if diff == 0:
            diff = self.zuoshou * 0.02 if self.zuoshou else 0.1

        self.ax_price.set_ylim(self.zuoshou - diff, self.zuoshou + diff)

        if self.zuoshou > 0:
            self.ax_pct.set_ylim(-diff / self.zuoshou * 100, diff / self.zuoshou * 100)
        else:
            self.ax_pct.set_ylim(-10, 10)

        if len(prices) > 0:
            self.ax_price.plot(indices, prices, color='#00a8ff', linewidth=1.5)
            self.ax_price.plot(indices, avgs, color='#f39c12', linewidth=1)

        self.hline_zuoshou.set_ydata([self.zuoshou, self.zuoshou])
        self.hline_zuoshou.set_visible(True)

        t1 = time.perf_counter()
        self.canvas.draw()
        t2 = time.perf_counter()
        logger.info(f"[Chart] code={base.get('code', 'N/A')} 绘图完成: 数据处理={(t1-t0)*1000:.1f}ms canvas.draw()={(t2-t1)*1000:.1f}ms 总计={(t2-t0)*1000:.1f}ms")

    def on_mouse_leave(self, event):
        try:
            if self.bg_cache and self.canvas:
                self.canvas.restore_region(self.bg_cache)
                self.canvas.blit(self.figure.bbox)
        except (RuntimeError, AttributeError):
            pass
        finally:
            if self.widget_wrapper:
                try:
                    self.widget_wrapper.crosshairSyncSignal.emit(-1)
                except Exception:
                    pass
            self._last_hover_idx = None
            self._is_dragging = False
