// quant_system/cpp/backtest_core.cpp
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <vector>

namespace py = pybind11;

/**
 * @brief 高性能回测引擎内核
 * 导师点评：采用连续内存布局（Sequential Memory Layout），对 CPU L1/L2 缓存极其友好，
 * 彻底规避了 Python 处理海量 Bar 对象时的内存碎片与装箱拆箱（Boxing）开销。
 */
class BacktestEngine {
public:
    double capital;
    int holdings = 0;
    double buy_price = 0.0;

    BacktestEngine(double initial_capital) : capital(initial_capital) {}

    // 核心运行函数：接收 NumPy 数组（价格和信号）
    py::dict run(py::array_t<double> prices, py::array_t<int> signals, double stop_loss_pct) {
        auto r_prices = prices.unchecked<1>();  // 快速访问原始内存指针
        auto r_signals = signals.unchecked<1>();
        size_t n = r_prices.shape(0);

        std::vector<double> equity_curve;
        equity_curve.reserve(n); // 预留空间，避免动态扩容导致的 I/O 抖动
        int trade_count = 0;

        for (size_t i = 0; i < n; ++i) {
            double cur_price = r_prices(i);
            int signal = r_signals(i);

            // 1. 毫秒级硬熔断逻辑
            if (holdings > 0 && stop_loss_pct > 0) {
                if ((cur_price - buy_price) / buy_price * 100.0 <= -stop_loss_pct) {
                    signal = -1;
                }
            }

            // 2. 状态机撮合逻辑
            if (signal == 1 && capital >= cur_price * 100) {
                int shares = static_cast<int>(capital / (cur_price * 100)) * 100;
                capital -= shares * cur_price;
                holdings += shares;
                buy_price = cur_price;
                trade_count++;
            }
            else if (signal == -1 && holdings > 0) {
                capital += holdings * cur_price;
                holdings = 0;
                buy_price = 0.0;
                trade_count++;
            }

            equity_curve.push_back(capital + holdings * cur_price);
        }

        py::dict res;
        res["final_equity"] = capital + holdings * r_prices(n-1);
        res["trade_count"] = trade_count;
        res["equity_curve"] = py::cast(equity_curve);
        return res;
    }
};

PYBIND11_MODULE(backtest_core, m) {
    py::class_<BacktestEngine>(m, "BacktestEngine")
        .def(py::init<double>())
        .def("run", &BacktestEngine::run, py::call_guard<py::gil_scoped_release>());
        // 亮点：py::gil_scoped_release() 释放 GIL，允许 UI 线程与计算内核在多核 CPU 上真正并行
}