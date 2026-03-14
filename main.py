import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from common.logger import setup_logger, global_exception_handler

def main():
    # 初始化日志
    logger = setup_logger()
    logger.info("程序启动")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()