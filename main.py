# main.py
import time
import builtins

# 1. 在程序最顶端注入全局启动时间，这里是程序运行的“绝对起点”
builtins.APP_START_TIME = time.perf_counter()
print(f"[性能计时] {0.0000:.4f}s | 程序开始运行，正在加载底层依赖库(PyQt/Pandas)...")

import sys
from PyQt6.QtWidgets import QApplication, QDialog
from ui.main_window import MainWindow
from common.logger import setup_logger
from login import LoginWindow, Session
import matplotlib

matplotlib.use('QtAgg')
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False


def main():
    print(f"[性能计时] {time.perf_counter() - APP_START_TIME:.4f}s | 依赖库加载完成，开始初始化主应用...")

    logger = setup_logger()
    logger.info("程序启动")

    from config import USE_DATABASE
    version = "数据库" if USE_DATABASE else "CSV"

    app = QApplication(sys.argv)

    print(f"[性能计时] {time.perf_counter() - APP_START_TIME:.4f}s | 正在构建并渲染主窗口界面...")
    # 优先实例化并显示主窗口
    window = MainWindow()
    window.show()
    print(f"[性能计时] {time.perf_counter() - APP_START_TIME:.4f}s | 主窗口已显示，正在加载子组件...")

    # 紧接着弹出登录框 (如果不需要强制登录，关闭弹窗即可)
    login_win = LoginWindow(window)
    if login_win.exec() == QDialog.DialogCode.Accepted:
        logger.info(f"用户登录成功: {Session.username}")
    else:
        logger.info("用户跳过登录，以游客身份进入（仅看盘）")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()