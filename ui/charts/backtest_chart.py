# ui/charts/backtest_chart.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QWidget, QVBoxLayout
import matplotlib.dates as mdates


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
        self.fig.subplots_adjust(left=0.08, right=0.96, top=0.95, bottom=0.08, hspace=0.15)
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
            dates = equity_df['date'].values
            returns = equity_df['total_return'].values
            drawdowns = equity_df['drawdown'].values

            # 计算每日独立收益率并填补空缺，使用现代 pandas 写法
            daily_pct = equity_df['equity'].pct_change().bfill().fillna(0) * 100

            # 3. 提取并对齐基准走势 (彻底修复 fillna(method) 报错)
            df_base = df.copy()
            df_base['date'] = pd.to_datetime(df_base['date'])

            # 建立以时间为基准的索引，对齐回测资金表的时间轴
            df_base = df_base.drop_duplicates(subset=['date']).set_index('date')
            df_base = df_base.reindex(equity_df['date'])

            # 【核心修复】：将旧的 .fillna(method='ffill') 改为现代 .ffill() 和 .bfill() 双重填补
            base_close = df_base['close'].ffill().bfill()

            if not base_close.empty and base_close.iloc[0] > 0:
                benchmark_returns = (base_close / base_close.iloc[0] - 1) * 100
            else:
                benchmark_returns = np.zeros(len(dates))

            # ================= 1. 上图：累计收益图 =================
            self.ax_equity.plot(dates, returns, label='策略累计收益 (%)', color='#ff5252', linewidth=2)
            self.ax_equity.plot(dates, benchmark_returns.values, label='基准参考收益 (%)', color='#2196F3',
                                linewidth=1.5, alpha=0.6)

            self.ax_equity.fill_between(dates, returns, 0, where=(returns >= 0), color='#ff5252', alpha=0.15)
            self.ax_equity.fill_between(dates, returns, 0, where=(returns < 0), color='#00e676', alpha=0.15)

            # 标注买卖点 (增加越界防御)
            buy_dates, buy_y, sell_dates, sell_y = [], [], [], []
            for t in trades:
                t_date = pd.to_datetime(t['date'])
                idx_matches = equity_df.index[equity_df['date'] == t_date].tolist()
                if idx_matches:
                    val = returns[idx_matches[0]]
                    if t['type'] == 'buy':
                        buy_dates.append(t_date)
                        buy_y.append(val)
                    elif t['type'] == 'sell':
                        sell_dates.append(t_date)
                        sell_y.append(val)

            if buy_dates:
                self.ax_equity.scatter(buy_dates, buy_y, marker='^', color='#ffeb3b', s=80, label='买入', zorder=5)
            if sell_dates:
                self.ax_equity.scatter(sell_dates, sell_y, marker='v', color='#00e676', s=80, label='卖出', zorder=5)

            self.ax_equity.set_title("策略核心效益表现", fontsize=14, fontweight='bold', color='#ffffff', pad=10)
            self.ax_equity.set_ylabel("累计收益(%)", fontsize=10, color='#aaaaaa')
            self.ax_equity.grid(True, linestyle='--', alpha=0.3)
            self.ax_equity.legend(loc='upper left', frameon=True, facecolor='#1e1e1e', edgecolor='#555555')

            # ================= 2. 中图：最大回撤图 =================
            self.ax_drawdown.plot(dates, drawdowns, color='#ff9800', linewidth=1)
            self.ax_drawdown.fill_between(dates, drawdowns, 0, color='#ff9800', alpha=0.4)
            self.ax_drawdown.set_ylabel("最大回撤(%)", fontsize=10, color='#aaaaaa')
            self.ax_drawdown.grid(True, linestyle='--', alpha=0.3)

            # ================= 3. 下图：每日收益率体状图 =================
            colors = ['#ff5252' if val >= 0 else '#00e676' for val in daily_pct]
            self.ax_daily.bar(dates, daily_pct.values, color=colors, width=1.0)
            self.ax_daily.set_ylabel("日收益(%)", fontsize=10, color='#aaaaaa')
            self.ax_daily.grid(True, linestyle='--', alpha=0.3)

            # ================= 坐标轴格式化 =================
            self.ax_daily.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            for label in self.ax_daily.get_xticklabels():
                label.set_rotation(15)
                label.set_horizontalalignment('right')

            # 隐藏上、中图的X轴时间标签，保持整洁
            plt.setp(self.ax_equity.get_xticklabels(), visible=False)
            plt.setp(self.ax_drawdown.get_xticklabels(), visible=False)

            # 重新绘制画布
            self.canvas.draw()

        except Exception as e:
            # 兜底捕获：如果绘图过程发生不可预见的崩溃，退回占位提示，防止闪退
            import traceback
            print(f"绘图发生异常: {e}")
            print(traceback.format_exc())
            self._draw_placeholder()
            self.ax_equity.text(0.5, 0.5, f"图表渲染失败:\n{str(e)}",
                                ha='center', va='center', color='#ff5252', fontsize=12)
            self.canvas.draw()