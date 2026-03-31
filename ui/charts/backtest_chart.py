# ui/charts/backtest_chart.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QWidget, QVBoxLayout
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter, MaxNLocator


class BacktestChart(QWidget):
    """高级量化回测可视化图表 (三图联动版)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 优化 matplotlib 全局暗黑现代样式
        plt.style.use('dark_background')
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['axes.facecolor'] = '#1e1e1e'
        plt.rcParams['figure.facecolor'] = '#1e1e1e'
        plt.rcParams['grid.color'] = '#333333'

        self.fig = Figure(figsize=(10, 10), dpi=100)
        # 调整边距，留出展示空间
        self.fig.subplots_adjust(left=0.08, right=0.96, top=0.88, bottom=0.15, hspace=0.40)
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        # 初始化上、中、下三个子图（比例 3:1:1）
        self.ax_equity = self.fig.add_subplot(5, 1, (1, 3))
        self.ax_drawdown = self.fig.add_subplot(5, 1, 4, sharex=self.ax_equity)
        self.ax_daily = self.fig.add_subplot(5, 1, 5, sharex=self.ax_equity)

        self._draw_placeholder()

    def _draw_placeholder(self):
        """初始占位提示"""
        for ax in [self.ax_equity, self.ax_drawdown, self.ax_daily]:
            ax.clear()
            ax.set_xticks([])
            ax.set_yticks([])

        self.ax_equity.text(0.5, 0.5, "在左侧或上方配置策略参数\n点击「运行策略回测」后此处将渲染多维效益图表",
                            ha='center', va='center', color='#888888', fontsize=14)
        self.canvas.draw()

    def draw(self, df: pd.DataFrame, equity_df: pd.DataFrame, trades: list):
        """绘制三维效益图"""
        # 1. 基础防御性检查
        for ax in [self.ax_equity, self.ax_drawdown, self.ax_daily]:
            ax.clear()

        if equity_df is None or equity_df.empty or df is None or df.empty:
            self._draw_placeholder()
            return

        try:
            # 2. 数据标准化与提取
            equity_df = equity_df.copy()
            equity_df['date'] = pd.to_datetime(equity_df['date'])

            # 【核心修复1】提取日期字符串，并使用纯粹的数字序号作为X轴，彻底消灭周末空缺断层
            dates_str = equity_df['date'].dt.strftime('%Y-%m-%d').tolist()
            indices = np.arange(len(dates_str))

            returns = equity_df['total_return'].values
            drawdowns = equity_df['drawdown'].values

            # 【核心修复2】去掉错误的 .bfill()，使用 .fillna(0) 确保第1天收益率为0，拒绝假数据
            daily_pct = equity_df['equity'].pct_change().fillna(0) * 100

            # 3. 提取并对齐基准走势
            df_base = df.copy()
            df_base['date'] = pd.to_datetime(df_base['date'])
            df_base = df_base.drop_duplicates(subset=['date']).set_index('date')
            df_base = df_base.reindex(equity_df['date'])
            base_close = df_base['close'].ffill().bfill()

            if not base_close.empty and base_close.iloc[0] > 0:
                benchmark_returns = (base_close / base_close.iloc[0] - 1) * 100
            else:
                benchmark_returns = np.zeros(len(indices))

            # ================= 1. 上图：累计收益图 =================
            self.ax_equity.plot(indices, returns, label='策略累计收益 (%)', color='#ff5252', linewidth=2)
            self.ax_equity.plot(indices, benchmark_returns.values, label='基准参考收益 (%)', color='#2196F3',
                                linewidth=1.5, alpha=0.6)

            # 加入 interpolate=True 让红绿填充在穿越 0 轴时更加严丝合缝
            self.ax_equity.fill_between(indices, returns, 0, where=(returns >= 0), color='#ff5252', alpha=0.15,
                                        interpolate=True)
            self.ax_equity.fill_between(indices, returns, 0, where=(returns < 0), color='#00e676', alpha=0.15,
                                        interpolate=True)

            # 标注买卖点 (精准映射到数字索引轴上)
            buy_idx, buy_y, sell_idx, sell_y = [], [], [], []
            for t in trades:
                t_date = pd.to_datetime(t['date']).strftime('%Y-%m-%d')
                if t_date in dates_str:
                    idx = dates_str.index(t_date)
                    val = returns[idx]
                    if t['type'] == 'buy':
                        buy_idx.append(idx)
                        buy_y.append(val)
                    elif t['type'] == 'sell':
                        sell_idx.append(idx)
                        sell_y.append(val)

            if buy_idx:
                self.ax_equity.scatter(buy_idx, buy_y, marker='^', color='#ffeb3b', s=80, label='买入', zorder=5)
            if sell_idx:
                self.ax_equity.scatter(sell_idx, sell_y, marker='v', color='#00e676', s=80, label='卖出', zorder=5)

            self.ax_equity.set_title("策略核心效益表现", fontsize=14, fontweight='bold', color='#ffffff', pad=10)
            self.ax_equity.set_ylabel("累计收益(%)", fontsize=10, color='#aaaaaa')
            self.ax_equity.grid(True, linestyle='--', alpha=0.3)
            self.ax_equity.legend(loc='upper left', frameon=True, facecolor='#1e1e1e', edgecolor='#555555')

            # ================= 2. 中图：最大回撤图 =================
            self.ax_drawdown.plot(indices, drawdowns, color='#ff9800', linewidth=1)
            self.ax_drawdown.fill_between(indices, drawdowns, 0, color='#ff9800', alpha=0.4)
            self.ax_drawdown.set_ylabel("最大回撤(%)", fontsize=10, color='#aaaaaa')
            self.ax_drawdown.grid(True, linestyle='--', alpha=0.3)

            # ================= 3. 下图：每日收益率体状图 =================
            colors = ['#ff5252' if val >= 0 else '#00e676' for val in daily_pct]
            self.ax_daily.bar(indices, daily_pct.values, color=colors, width=0.8)
            self.ax_daily.set_ylabel("日收益(%)", fontsize=10, color='#aaaaaa')
            self.ax_daily.grid(True, linestyle='--', alpha=0.3)

            # ================= 坐标轴格式化 =================
            # 【核心修复3】使用回调函数，将数字 X 轴重新映射回真实的文字日期
            def format_date(x, pos=None):
                idx = int(np.clip(np.round(x), 0, len(dates_str) - 1))
                return dates_str[idx] if 0 <= x < len(dates_str) else ""

            self.ax_daily.xaxis.set_major_formatter(FuncFormatter(format_date))
            self.ax_daily.xaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))

            for label in self.ax_daily.get_xticklabels():
                label.set_rotation(0)
                label.set_horizontalalignment('center')

            # 隐藏上、中图的X轴时间标签
            plt.setp(self.ax_equity.get_xticklabels(), visible=False)
            plt.setp(self.ax_drawdown.get_xticklabels(), visible=False)

            # 限制全局 X 轴范围，切掉两端多余的黑边
            self.ax_equity.set_xlim(-1, len(indices))

            # 重新绘制画布
            self.canvas.draw()

        except Exception as e:
            import traceback
            print(f"绘图发生异常: {e}")
            print(traceback.format_exc())
            self._draw_placeholder()
            self.ax_equity.text(0.5, 0.5, f"图表渲染失败:\n{str(e)}",
                                ha='center', va='center', color='#ff5252', fontsize=12)
            self.canvas.draw()