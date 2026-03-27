import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from scipy.interpolate import make_interp_spline
from matplotlib.ticker import MultipleLocator


class FenshiChart:
    """专业分时图：支持全字段展示（已去掉金额）、双击开关信息牌、单击自由拖拽"""

    def __init__(self, wrapper=None):
        self.widget_wrapper = wrapper
        self.bg_color = '#1e1e1e'
        self.zuoshou = 0
        self.bg_cache = None
        self._last_hover_idx = None
        self.hover_data_map = {}

        # --- 交互状态 ---
        self.tooltip_visible = False  # 默认隐藏，双击切换
        self._is_dragging = False
        self.tooltip_pos = [0.02, 0.96]  # 初始位置：左上角 (坐标范围 0-1)
        self._drag_offset = (0, 0)

        self.figure = Figure(figsize=(10, 6), facecolor=self.bg_color)
        self.canvas = FigureCanvas(self.figure)
        self.figure.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.1)
        self.ax_price = self.figure.add_subplot(111, facecolor=self.bg_color)
        self.ax_pct = self.ax_price.twinx()

        self._init_cursor_artists()

        # 绑定事件
        self.canvas.mpl_connect("draw_event", self.on_draw_event)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("axes_leave_event", self.on_mouse_leave)
        self.canvas.mpl_connect("button_press_event", self.on_mouse_press)
        self.canvas.mpl_connect("button_release_event", self.on_mouse_release)
        self._setup_axes()

    def _init_cursor_artists(self):
        """初始化十字光标和悬浮信息牌"""
        self.v_line = self.ax_price.axvline(x=0, color='white', linestyle=':', visible=False, animated=True)
        self.h_line = self.ax_price.axhline(y=0, color='white', linestyle=':', visible=False, animated=True)

        # 信息牌文字块 (初始设为不可见)
        self.tooltip = self.ax_price.annotate(
            "", xy=tuple(self.tooltip_pos), xycoords="axes fraction",
            bbox=dict(boxstyle="round,pad=0.5", fc="#2a2a2a", ec="#666666", alpha=0.95),
            color="#eeeeee", visible=False, animated=True, zorder=100, fontsize=10,
            va='top', ha='left'
        )
        self.hline_zuoshou = self.ax_price.axhline(y=0, color='#444444', linewidth=2, zorder=3, visible=False)

    def on_draw_event(self, event):
        """保存背景缓存，用于 blit 高性能刷新"""
        self.bg_cache = self.canvas.copy_from_bbox(self.figure.bbox)

    def on_mouse_press(self, event):
        """处理鼠标按下：双击切换显示，左键按住拖动"""
        if event.button != 1: return

        # 1. 检测双击：切换信息牌显示/隐藏
        if event.dblclick:
            self.tooltip_visible = not self.tooltip_visible
            self._do_blit()
            return

        # 2. 如果信息牌已显示，检测是否开始拖拽
        if self.tooltip_visible:
            inv = self.ax_price.transAxes.inverted()
            mx, my = inv.transform((event.x, event.y))
            tx, ty = self.tooltip_pos
            # 判定点击区域：点击在信息牌文字框大致范围内即可拖动
            if tx <= mx <= tx + 0.35 and ty - 0.55 <= my <= ty:
                self._is_dragging = True
                self._drag_offset = (mx - tx, my - ty)

    def on_mouse_release(self, event):
        """鼠标松开：结束拖拽状态"""
        self._is_dragging = False

    def on_mouse_move(self, event):
        """鼠标移动：处理信息牌拖拽或十字线追踪"""
        if not self.bg_cache: return

        inv = self.ax_price.transAxes.inverted()
        mx, my = inv.transform((event.x, event.y))

        # 1. 处理拖拽逻辑
        if self._is_dragging:
            # 限制拖动范围，防止信息牌飞出图表
            new_x = np.clip(mx - self._drag_offset[0], 0, 0.65)
            new_y = np.clip(my - self._drag_offset[1], 0.55, 1.0)
            self.tooltip_pos = [new_x, new_y]
            self.tooltip.xy = tuple(self.tooltip_pos)
            self._do_blit()
            return

        # 2. 处理常规十字线追踪 (仅在绘图区内)
        if not event.inaxes: return
        x_idx = int(round(event.xdata))
        if x_idx not in self.hover_data_map or x_idx == self._last_hover_idx: return

        self._last_hover_idx = x_idx
        p = self.hover_data_map[x_idx]

        self.v_line.set_xdata([x_idx, x_idx])
        self.h_line.set_ydata([p['price'], p['price']])

        # 信息牌字段补全：已去掉金额
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
        """执行高性能局部重绘"""
        try:
            self.canvas.restore_region(self.bg_cache)
            # 十字线始终随鼠标显示
            for art in [self.v_line, self.h_line]:
                art.set_visible(True)
                self.ax_price.draw_artist(art)

            # 信息牌根据开关状态显示
            if self.tooltip_visible:
                self.tooltip.set_visible(True)
                self.ax_price.draw_artist(self.tooltip)
            else:
                self.tooltip.set_visible(False)

            self.canvas.blit(self.figure.bbox)
        except:
            pass

    def _setup_axes(self):
        """设置坐标轴基础样式"""
        self.ax_price.set_xlim(0, 240)
        self.ax_price.set_xticks([0, 60, 120, 180, 240])
        self.ax_price.set_xticklabels(["09:30", "10:30", "11:30/13:00", "14:00", "15:00"], color='#cccccc', fontsize=8)
        self.ax_price.grid(True, which='both', color='#333333', linestyle='--', alpha=0.5)

    def draw(self, df, base):
        """绘制分时图主数据"""
        if df.empty: return
        self.hover_data_map = {}
        prices, avgs, indices = [], [], []

        for row in df.itertuples():
            h, m = map(int, row.time.split(':'))
            # 将时间换算为 0-240 索引
            idx = (h * 60 + m - 570) if h * 60 + m <= 690 else (h * 60 + m - 780 + 120)
            if 0 <= idx <= 240:
                indices.append(idx)
                prices.append(row.price)
                avgs.append(row.avg_price)

                # 补全行情字段映射（含单位换算）
                self.hover_data_map[idx] = {
                    'time': row.time,
                    'price': row.price,
                    'avg_price': row.avg_price,
                    'pct_chg': row.pct_chg,
                    'vol': getattr(row, 'minute_volume', 0),
                    'huan_shou': getattr(row, 'huan_shou', 0),
                    'liang_bi': getattr(row, 'liang_bi', 0),
                    'wei_bi': getattr(row, 'wei_bi', 0),
                    'nei_pan': getattr(row, 'nei_pan', 0),
                    'wai_pan': getattr(row, 'wai_pan', 0)
                }

        self.zuoshou = base.get('ZuoShou', prices[0])
        diff = max(abs(max(prices) - self.zuoshou), abs(self.zuoshou - min(prices))) * 1.1
        self.ax_price.set_ylim(self.zuoshou - diff, self.zuoshou + diff)
        self.ax_pct.set_ylim(-diff / self.zuoshou * 100, diff / self.zuoshou * 100)

        self.ax_price.plot(indices, prices, color='#00a8ff', linewidth=1.5)
        self.ax_price.plot(indices, avgs, color='#f39c12', linewidth=1)
        self.hline_zuoshou.set_ydata([self.zuoshou, self.zuoshou])
        self.hline_zuoshou.set_visible(True)
        self.canvas.draw()

    def on_mouse_leave(self, event):
        """鼠标移出图表"""
        if self.bg_cache:
            self.canvas.restore_region(self.bg_cache)
            self.canvas.blit(self.figure.bbox)
        if self.widget_wrapper:
            self.widget_wrapper.crosshairSyncSignal.emit(-1)
        self._last_hover_idx = None
        self._is_dragging = False