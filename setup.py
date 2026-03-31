# 文件路径: setup.py
from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext
import sys

# Windows (MSVC) 使用 /O2，其他系统 (GCC/Clang) 使用 -O3
compile_args = ["/O2"] if sys.platform == "win32" else ["-O3"]

ext_modules = [
    Pybind11Extension(
        "backtest_core",
        ["cpp/backtest_core.cpp"],  # 修复了路径：去掉了前缀 quant_system/
        extra_compile_args=compile_args, # 修复了 Windows 下的编译警告
    ),
]

setup(
    name="backtest_core",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)