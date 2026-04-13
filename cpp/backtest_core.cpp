#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <vector>
#include <iostream>
#include <stdexcept>

namespace py = pybind11;

class BacktestEngine {
public:
    double capital;
    int holdings = 0;
    double buy_price = 0.0;

    BacktestEngine(double initial_capital) : capital(initial_capital) {}

    py::dict run(py::array_t<double, py::array::c_style | py::array::forcecast> prices,
                 py::array_t<int, py::array::c_style | py::array::forcecast> signals,
                 double stop_loss_pct) {
        
        py::dict res;
        try {
            if (prices.ndim() != 1 || signals.ndim() != 1) {
                throw std::runtime_error("Input arrays must be 1D");
            }
            auto r_prices = prices.unchecked<1>();
            auto r_signals = signals.unchecked<1>();
            size_t n = r_prices.shape(0);

            std::vector<double> equity_curve;
            equity_curve.reserve(n);
            std::vector<std::vector<double>> trades;
            trades.reserve(1000);

            int trade_count = 0;
            double final_price = 0.0;

            if (n > 0) {
                {
                    py::gil_scoped_release release;
                    for (size_t i = 0; i < n; ++i) {
                        double cur_price = r_prices(i);
                        int signal = r_signals(i);
                        if (holdings > 0 && stop_loss_pct > 0) {
                            if ((cur_price - buy_price) / buy_price * 100.0 <= -stop_loss_pct) signal = -1;
                        }
                        if (signal == 1 && capital >= cur_price * 100) {
                            int shares = static_cast<int>(capital / (cur_price * 100)) * 100;
                            if (shares > 0) {
                                capital -= shares * cur_price;
                                holdings += shares;
                                buy_price = cur_price;
                                trade_count++;
                                trades.push_back({static_cast<double>(i), 1.0, cur_price, static_cast<double>(shares)});
                            }
                        }
                        else if (signal == -1 && holdings > 0) {
                            capital += holdings * cur_price;
                            trades.push_back({static_cast<double>(i), -1.0, cur_price, static_cast<double>(holdings)});
                            holdings = 0;
                            buy_price = 0.0;
                            trade_count++;
                        }
                        equity_curve.push_back(capital + holdings * cur_price);
                        if (i == n - 1) final_price = cur_price;
                    }
                }
            }
            res["final_equity"] = capital + holdings * final_price;
            res["trade_count"] = trade_count;
            res["equity_curve"] = py::cast(equity_curve);
            res["trades"] = py::cast(trades);
        } catch (const std::exception& e) {
            throw;
        }
        return res;
    }
};

PYBIND11_MODULE(backtest_core, m) {
    py::class_<BacktestEngine>(m, "BacktestEngine")
        .def(py::init<double>())
        .def("run", &BacktestEngine::run);
}