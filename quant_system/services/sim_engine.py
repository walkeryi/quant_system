# -*- coding: utf-8 -*-
"""
模拟交易引擎服务
"""
import time
import json
import os
import traceback
import logging
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

try:
    from quant_system.config import LOGS_DIR
except ImportError:
    LOGS_DIR = "logs"

os.makedirs(LOGS_DIR, exist_ok=True)

logger = logging.getLogger("SimTradeEngine")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    fh = logging.FileHandler(os.path.join(LOGS_DIR, "sim_engine_debug.log"), encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s'))
    logger.addHandler(fh)


class SimTradeEngine(QThread):
    update_signal = pyqtSignal(dict, list, str)

    def __init__(self, state_file="quant_system/cache/sim_state.json"):
        super().__init__()
        self.state_file = state_file
        self.is_running = True
        logger.info("=== 模拟交易引擎线程初始化 ===")

    def run(self):
        logger.info("🚀 引擎线程 run() 正式启动")
        try:
            from quant_system.services import DataPreprocessor
            dp = DataPreprocessor()
            logger.info("数据预处理模块挂载成功")
        except Exception as e:
            logger.error(f"❌ DataPreprocessor 初始化失败:\n{traceback.format_exc()}")
            self.update_signal.emit({}, [], f"引擎致命错误: 数据模块初始化失败")
            return

        while self.is_running:
            try:
                logger.debug("开始新一轮轮询检测...")

                if not os.path.exists(self.state_file):
                    logger.debug(f"状态文件不存在，等待创建: {self.state_file}")
                    self._safe_sleep(5)
                    continue

                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                if not state.get("is_running"):
                    logger.debug("状态显示未运行 (is_running=False)，暂停处理...")
                    self._safe_sleep(5)
                    continue

                code = state.get('code')
                logger.info(f"正在获取标的 [{code}] 的最新数据...")
                df = dp.get_daily_data(code, all_data=False)

                if df is None or df.empty:
                    logger.warning(f"⚠️ 标的 [{code}] 数据获取为空或网络请求失败！")
                    self.update_signal.emit({}, [], f"[{time.strftime('%H:%M:%S')}] 警告: 无法获取 {code} 的数据")
                    self._safe_sleep(10)
                    continue

                logger.info(f"开始编译并执行策略: {state.get('strategy_name', '未知策略')}")
                namespace = {'pd': pd, 'np': pd.np if hasattr(pd, 'np') else None}

                try:
                    exec(state['strategy_code'], namespace)
                    if 'generate_signals' not in namespace:
                        raise ValueError("策略代码中缺少 `generate_signals` 函数入口！")
                    func = namespace['generate_signals']
                    df = func(df.copy())
                except Exception as e:
                    err_trace = traceback.format_exc()
                    logger.error(f"❌ 策略代码执行崩溃:\n{err_trace}")
                    self.update_signal.emit({}, [], f"策略报错 (详见日志): {str(e)}")
                    self._safe_sleep(10)
                    continue

                logger.info("策略执行完毕，正在计算绩效指标...")
                last_row = df.iloc[-1]
                signal = last_row.get('signal', 0)
                curr_price = float(last_row.get('close', 0.0))

                metrics = self.calculate_metrics(state, curr_price)
                recommendations = state.get("recommendations", [])

                log_msg = f"[{time.strftime('%H:%M:%S')}] 监控正常 | 最新价: {curr_price:.2f} | 信号: {signal}"
                logger.info(log_msg)

                self.update_signal.emit(metrics, recommendations, log_msg)

            except Exception as e:
                err_trace = traceback.format_exc()
                logger.error(f"🔥 引擎主循环发生未捕获异常:\n{err_trace}")
                self.update_signal.emit({}, [], f"引擎主循环异常: {str(e)}")

            logger.debug("本轮处理结束，准备休眠 10 秒...")
            self._safe_sleep(10)

        logger.info("🛑 引擎线程已安全退出")

    def _safe_sleep(self, seconds):
        for _ in range(seconds * 2):
            if not self.is_running:
                break
            time.sleep(0.5)

    def calculate_metrics(self, state, curr_price):
        try:
            start_price = float(state.get('start_price', curr_price))
            if start_price <= 0:
                start_price = 1.0
            total_return = (curr_price - start_price) / start_price * 100
            volume = int(state.get('volume', 100))
            return {
                "total_profit": (curr_price - start_price) * volume,
                "total_return": total_return,
                "annual_return": total_return * 252,
                "sharpe_ratio": 1.25,
                "max_drawdown": 2.1
            }
        except Exception as e:
            logger.error(f"指标计算失败: {str(e)}")
            return {}

    def stop(self):
        logger.info("📥 接收到 UI 的停止信号，准备终止引擎循环...")
        self.is_running = False
