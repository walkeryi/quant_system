# ui/charts/fenshi_chart.py
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from scipy.interpolate import make_interp_spline

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

class FenshiChart:
    def __init__(self):
        # 1. 基础配置
        self.bg_color = '#1e1e1e'
        self.grid_color = '#333333'
        self.major_grid_color = '#555555'
        self.text_color = '#cccccc'
        self.price_color = '#00a8ff'
        self.avg_color = '#f39c12'
        self.zuoshou_color = '#444444'  # 加粗灰色中线
        self.crosshair_color = '#ffffff'

        # 2. 创建画布与轴
        self.figure = Figure(figsize=(10, 6), facecolor=self.bg_color)
        self.canvas = FigureCanvas(self.figure)
        self.figure.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.15)
        self.ax_price = self.figure.add_subplot(111, facecolor=self.bg_color)
        self.ax_pct = self.ax_price.twinx()

        # 3. 静态数据对象
        self.line_price, = self.ax_price.plot([], [], color=self.price_color, linewidth=2, zorder=4)
        self.line_avg, = self.ax_price.plot([], [], color=self.avg_color, linewidth=1.5, zorder=4)
        self.hline_zuoshou = self.ax_price.axhline(y=0, color=self.zuoshou_color, linestyle='-', linewidth=2.5,
                                                   zorder=3, visible=False)

        # 4. 交互组件 (使用 animated=True 优化性能)
        self.v_line = self.ax_price.axvline(x=0, color=self.crosshair_color, linestyle=':', linewidth=0.8,
                                            visible=False, animated=True, zorder=10)
        self.h_line = self.ax_price.axhline(y=0, color=self.crosshair_color, linestyle=':', linewidth=0.8,
                                            visible=False, animated=True, zorder=10)

        bbox_props = dict(boxstyle="square,pad=0.2", fc="black", ec=self.crosshair_color, lw=0.5)
        self.label_price = self.ax_price.text(0, 0, "", color="white", bbox=bbox_props, ha="right", va="center",
                                              visible=False, animated=True, zorder=15)
        self.label_pct = self.ax_pct.text(240, 0, "", color="white", bbox=bbox_props, ha="left", va="center",
                                          visible=False, animated=True, zorder=15)
        self.label_time = self.ax_price.text(0, 0, "", color="white", bbox=bbox_props, ha="center", va="top",
                                             visible=False, animated=True, zorder=15)

        self.tooltip = self.ax_price.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
                                              bbox=dict(boxstyle="round,pad=0.4", fc="#2a2a2a", ec="#666666",
                                                        alpha=0.9),
                                              color="#eeeeee", visible=False, animated=True, zorder=20, fontsize=9)

        self._setup_static_framework()
        self.hover_data_map = {}
        self.zuoshou = 0
        self._last_hover_idx = None
        self.bg_cache = None

        self.draw_placeholder(draw_canvas=False)

        # 事件绑定
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("axes_leave_event", self.on_mouse_leave)
        self.canvas.mpl_connect("resize_event", self.on_resize)

    def time_to_index(self, t_str):
        try:
            h, m = map(int, t_str.split(':'))
            minutes = h * 60 + m
            if 570 <= minutes <= 690:
                return minutes - 570
            elif 780 <= minutes <= 900:
                return minutes - 780 + 120
        except:
            pass
        return None

    def _setup_static_framework(self):
        """搭建固定的坐标轴刻度与网格"""
        for ax in [self.ax_price, self.ax_pct]:
            ax.tick_params(axis='y', colors=self.text_color, labelsize=9)
            ax.spines['bottom'].set_color(self.grid_color)
            ax.spines['top'].set_color(self.grid_color)
            ax.spines['left'].set_color(self.grid_color)
            ax.spines['right'].set_color(self.grid_color)

        self.ax_price.set_xlim(0, 240)
        self.ax_price.set_xticks([0, 30, 60, 90, 120, 150, 180, 210, 240])
        self.ax_price.set_xticklabels(
            ["09:30", "10:00", "10:30", "11:00", "11:30/13:00", "13:30", "14:00", "14:30", "15:00"], fontsize=8,
            color=self.text_color)
        self.ax_price.set_xticks([15, 45, 75, 105, 135, 165, 195, 225], minor=True)
        self.ax_price.grid(True, which='major', axis='y', color=self.grid_color, linestyle='--', linewidth=0.5)
        self.ax_price.grid(True, which='major', axis='x', color=self.major_grid_color, linestyle='-', linewidth=1.2)
        self.ax_price.grid(True, which='minor', axis='x', color=self.grid_color, linestyle='--', linewidth=0.5)

    def _smooth_data(self, x, y):
        """去重并进行三次样条平滑插值"""
        if len(x) < 4: return x, y
        unique_x, indices = np.unique(x, return_index=True)
        unique_y = np.array(y)[indices]
        if len(unique_x) < 4: return unique_x, unique_y
        x_new = np.linspace(unique_x.min(), unique_x.max(), len(unique_x) * 3)
        return x_new, make_interp_spline(unique_x, unique_y, k=3)(x_new)

    def draw_placeholder(self, draw_canvas=True):
        self.line_price.set_data([], [])
        self.line_avg.set_data([], [])
        self.hline_zuoshou.set_visible(False)
        self.ax_price.set_title("分时图 (等待数据...)", color=self.text_color, fontsize=12)
        if draw_canvas:
            self.canvas.draw()
            self.bg_cache = self.canvas.copy_from_bbox(self.figure.bbox)

    def draw(self, df, base):
        self.hover_data_map.clear()
        self._last_hover_idx = None
        self.bg_cache = None
        if df.empty: return self.draw_placeholder()

        indices, prices, avgs = [], [], []
        for row in df.itertuples(index=False):
            idx = self.time_to_index(row.time)
            if idx is not None:
                indices.append(idx)
                prices.append(row.price)
                avgs.append(row.avg_price)
                self.hover_data_map[idx] = {'time': row.time, 'price': row.price, 'avg': row.avg_price,
                                            'vol': getattr(row, 'volume', 0)}

        if not prices: return self.draw_placeholder()
        self.zuoshou = base.get('zuoshou', prices[0])
        limit_diff = max(abs(max(prices) - self.zuoshou), abs(self.zuoshou - min(prices))) * 1.1
        if limit_diff == 0: limit_diff = self.zuoshou * 0.005

        self.ax_price.set_ylim(self.zuoshou - limit_diff, self.zuoshou + limit_diff)
        self.ax_pct.set_ylim(-limit_diff / self.zuoshou * 100, limit_diff / self.zuoshou * 100)

        # 平滑处理
        s_idx, s_prices = self._smooth_data(indices, prices)
        _, s_avgs = self._smooth_data(indices, avgs)

        self.hline_zuoshou.set_ydata([self.zuoshou, self.zuoshou])
        self.hline_zuoshou.set_visible(True)
        self.line_price.set_data(s_idx, s_prices)
        self.line_avg.set_data(s_idx, s_avgs)
        self.ax_price.set_title(f"{base.get('name')} ({base.get('code')})", color=self.text_color)
        self.canvas.draw()
        self.bg_cache = self.canvas.copy_from_bbox(self.figure.bbox)

    def on_resize(self, event):
        self.canvas.draw()
        self.bg_cache = self.canvas.copy_from_bbox(self.figure.bbox)

    def on_mouse_leave(self, event):
        self._last_hover_idx = None
        if self.bg_cache:
            self.canvas.restore_region(self.bg_cache)
            self.canvas.blit(self.figure.bbox)

    def on_mouse_move(self, event):
        if not event.inaxes or not self.hover_data_map: return
        x_idx = int(round(event.xdata))
        if x_idx == self._last_hover_idx or x_idx not in self.hover_data_map: return
        self._last_hover_idx = x_idx

        p = self.hover_data_map[x_idx]
        pct = (p['price'] - self.zuoshou) / self.zuoshou * 100

        self.v_line.set_xdata([x_idx, x_idx])
        self.h_line.set_ydata([p['price'], p['price']])
        self.label_price.set_text(f"{p['price']:.2f}")
        self.label_price.set_position((0, p['price']))
        self.label_pct.set_text(f"{pct:+.2f}%")
        self.label_pct.set_position((240, pct))
        self.label_time.set_text(p['time'])
        self.label_time.set_position((x_idx, self.ax_price.get_ylim()[0]))

        # 弹窗内容更新
        self.tooltip.set_text(
            f"时间: {p['time']}\n价格: {p['price']:.2f}\n涨幅: {pct:+.2f}%\n量: {p['vol'] / 100:.0f}手")
        self.tooltip.xy = (x_idx, p['price'])
        self.tooltip.set_ha("right" if x_idx > 120 else "left")

        if self.bg_cache:
            self.canvas.restore_region(self.bg_cache)
            self.v_line.set_visible(True)
            self.h_line.set_visible(True)
            self.label_price.set_visible(True)
            self.label_pct.set_visible(True)
            self.label_time.set_visible(True)
            self.tooltip.set_visible(True)
            self.ax_price.draw_artist(self.v_line)
            self.ax_price.draw_artist(self.h_line)
            self.ax_price.draw_artist(self.label_price)
            self.ax_pct.draw_artist(self.label_pct)
            self.ax_price.draw_artist(self.label_time)
            self.ax_price.draw_artist(self.tooltip)
            self.canvas.blit(self.figure.bbox)