import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from scipy.interpolate import make_interp_spline
from matplotlib.ticker import MultipleLocator

class FenshiChart:
    def __init__(self, wrapper=None):
        self.widget_wrapper = wrapper
        self.bg_color = '#1e1e1e'
        self.zuoshou = 0
        self.bg_cache = None
        self._last_hover_idx = None
        # 【修复】：必须在初始化时定义，防止 on_mouse_move 报错
        self.hover_data_map = {}

        self.figure = Figure(figsize=(10, 6), facecolor=self.bg_color)
        self.canvas = FigureCanvas(self.figure)
        # 【修复】：right 设为 0.92，解决 left >= right 崩溃
        self.figure.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.1)
        self.ax_price = self.figure.add_subplot(111, facecolor=self.bg_color)
        self.ax_pct = self.ax_price.twinx()

        self.line_price, = self.ax_price.plot([], [], color='#00a8ff', linewidth=2, zorder=4)
        self.line_avg, = self.ax_price.plot([], [], color='#f39c12', linewidth=1.5, zorder=4)
        self.hline_zuoshou = self.ax_price.axhline(y=0, color='#444444', linewidth=2.5, zorder=3, visible=False)

        self.v_line = self.ax_price.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)
        self.h_line = self.ax_price.axhline(y=0, color='white', linestyle=':', visible=False, animated=True)
        self.tooltip = self.ax_price.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.4", fc="#2a2a2a", ec="#666666", alpha=0.9),
            color="#eeeeee", visible=False, animated=True, zorder=20, fontsize=9)

        self.canvas.mpl_connect("draw_event", self.on_draw_event)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("axes_leave_event", self.on_mouse_leave)
        self._setup_axes()

    def on_draw_event(self, event):
        self.bg_cache = self.canvas.copy_from_bbox(self.figure.bbox)

    def _setup_axes(self):
        for ax in [self.ax_price, self.ax_pct]:
            ax.tick_params(axis='y', colors='#cccccc', labelsize=9)
            for spine in ax.spines.values(): spine.set_color('#333333')
        self.ax_price.set_xlim(0, 240)
        self.ax_price.set_xticks([0, 30, 60, 90, 120, 150, 180, 210, 240])
        self.ax_price.set_xticklabels(
            ["09:30", "10:00", "10:30", "11:00", "11:30/13:00", "13:30", "14:00", "14:30", "15:00"], fontsize=8,
            color='#cccccc')

        # --- 新增：大格与小格刻度网格 ---
        self.ax_price.xaxis.set_minor_locator(MultipleLocator(15))  # 15分钟小格
        self.ax_price.grid(True, which='major', axis='x', color='#444444', linestyle='-', linewidth=0.8)  # 大格主网格
        self.ax_price.grid(True, which='minor', axis='x', color='#333333', linestyle='--', linewidth=0.5)  # 小格次网格

        self.ax_price.grid(True, which='major', axis='y', color='#333333', linestyle='--')

    def draw(self, df, base):
        self.hover_data_map = {}
        self._last_hover_idx = None
        if df.empty: return
        indices, prices, avgs = [], [], []
        for row in df.itertuples(index=False):
            h, m = map(int, row.time.split(':'))
            idx = (h * 60 + m - 570) if h * 60 + m <= 690 else (h * 60 + m - 780 + 120)
            if 0 <= idx <= 240:
                indices.append(idx); prices.append(row.price); avgs.append(row.avg_price)
                self.hover_data_map[idx] = \
                    {
                        'time': row.time,
                        'price': row.price,
                        'avg_price': row.avg_price,
                        'pct_chg': row.pct_chg,
                        'vol': getattr(row, 'minute_volume', 0),
                        'nei_pan': getattr(row, 'nei_pan', 0),
                        'wai_pan': getattr(row, 'wai_pan', 0),
                        'huan_shou': getattr(row, 'huan_shou', 0),
                        'liang_bi': getattr(row, 'liang_bi', 0),
                        'wei_bi': getattr(row, 'wei_bi', 0),
                    }

        u_idx, u_pos = np.unique(indices, return_index=True)
        u_prices, u_avgs = np.array(prices)[u_pos], np.array(avgs)[u_pos]

        self.zuoshou = base.get('ZuoShou', u_prices[0])
        diff = max(abs(max(u_prices) - self.zuoshou), abs(self.zuoshou - min(u_prices))) * 1.1
        if diff <= 0: diff = self.zuoshou * 0.01

        # 【核心】：左右各 13 个等间距对称刻度
        y_max, y_min = self.zuoshou + diff, self.zuoshou - diff
        self.ax_price.set_ylim(y_min, y_max)
        price_ticks = np.linspace(y_max, y_min, 13)
        self.ax_price.set_yticks(price_ticks)
        self.ax_price.set_yticklabels([f"{p:.2f}" for p in price_ticks])

        limit_pct = (diff / self.zuoshou * 100) if self.zuoshou > 0 else 0
        self.ax_pct.set_ylim(-limit_pct, limit_pct)
        self.ax_pct.set_yticks(np.linspace(limit_pct, -limit_pct, 13))
        self.ax_pct.set_yticklabels([f"{p:+.2f}%" for p in np.linspace(limit_pct, -limit_pct, 13)])

        if len(u_idx) > 3:
            x_new = np.linspace(u_idx.min(), u_idx.max(), len(u_idx) * 3)
            self.line_price.set_data(x_new, make_interp_spline(u_idx, u_prices)(x_new))
            self.line_avg.set_data(x_new, make_interp_spline(u_idx, u_avgs)(x_new))
        else:
            self.line_price.set_data(u_idx, u_prices); self.line_avg.set_data(u_idx, u_avgs)

        self.hline_zuoshou.set_ydata([self.zuoshou, self.zuoshou]); self.hline_zuoshou.set_visible(True)
        self.canvas.draw()

    def on_mouse_move(self, event):
        if not event.inaxes or not self.bg_cache: return
        x_idx = int(round(event.xdata))
        if x_idx not in self.hover_data_map or x_idx == self._last_hover_idx: return
        self._last_hover_idx = x_idx
        p = self.hover_data_map[x_idx]
        pct = ((p['price'] - self.zuoshou) / self.zuoshou * 100) if self.zuoshou > 0 else 0.0

        self.v_line.set_xdata([x_idx, x_idx]); self.h_line.set_ydata([p['price'], p['price']])
        self.tooltip.set_text(
            f"{p['time']}\n"
            f"价格: {p['price']:.2f}\n"
            f"涨幅: {pct:+.2f}%\n"
            f"均价: {p['avg_price']:.2f}\n"
            f"成交量: {p['vol']:.0f}手\n"
            f"内盘: {p['nei_pan']:.0f}  外盘: {p['wai_pan']:.0f}\n"
            f"换手: {p['huan_shou']:.2f}%\n"
            f"量比: {p['liang_bi']:.2f}\n"
            f"委比: {p['wei_bi']:.2f}%"
        )
        self.tooltip.xy = (x_idx, p['price'])

        self.canvas.restore_region(self.bg_cache)
        for art in [self.v_line, self.h_line, self.tooltip]:
            art.set_visible(True); self.ax_price.draw_artist(art)
        self.canvas.blit(self.figure.bbox)
        if self.widget_wrapper: self.widget_wrapper.crosshairSyncSignal.emit(x_idx)

    def on_mouse_leave(self, event):
        if self.bg_cache: self.canvas.restore_region(self.bg_cache); self.canvas.blit(self.figure.bbox)
        if self.widget_wrapper: self.widget_wrapper.crosshairSyncSignal.emit(-1)