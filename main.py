# main.py
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from common.logger import setup_logger

def main():
    # 初始化日志
    logger = setup_logger()
    logger.info("程序启动")

    # 打印当前数据版本
    from config import USE_DATABASE
    version = "数据库" if USE_DATABASE else "CSV"
    print(f"当前数据版本: {version}")
    logger.info(f"当前数据版本: {version}")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()