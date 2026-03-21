# login.py
import os
import csv
import hashlib
import json
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QMessageBox, QFormLayout,
                             QLabel, QTabWidget, QWidget, QComboBox, QCheckBox)

from config import USERS_CSV

# 本地记住密码的存储文件
SAVED_USERS_FILE = os.path.join(os.path.dirname(USERS_CSV), "saved_users.json")


# 全局会话信息，供 API 接口调用当前用户的凭证
class Session:
    username = ""
    mykey = ""
    is_logged_in = False  # 登录状态标记


def md5_encrypt(password):
    return hashlib.md5(password.encode('utf-8')).hexdigest()


def init_users_csv():
    if not os.path.exists(USERS_CSV):
        os.makedirs(os.path.dirname(USERS_CSV), exist_ok=True)
        with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['username', 'password', 'mykey'])
            writer.writerow(['admin', md5_encrypt('123456'), ''])
    else:
        with open(USERS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, [])
            rows = list(reader)

        if 'mykey' not in header:
            with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['username', 'password', 'mykey'])
                for r in rows:
                    if len(r) >= 2:
                        writer.writerow([r[0], r[1], ''])


def verify_user(username, password):
    if not os.path.exists(USERS_CSV):
        return False, ""
    with open(USERS_CSV, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['username'] == username and row['password'] == md5_encrypt(password):
                return True, row.get('mykey', '')
    return False, ""


def register_user(username, password, mykey):
    if os.path.exists(USERS_CSV):
        with open(USERS_CSV, 'r', encoding='utf-8') as f:
            if username in [row['username'] for row in csv.DictReader(f)]:
                return False
    with open(USERS_CSV, 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([username, md5_encrypt(password), mykey])
    return True


class LoginWindow(QDialog):
    # 增加 parent=None 使其能悬浮在主窗口之上
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("量化系统 - 交易授权")
        self.setFixedSize(320, 260)
        init_users_csv()

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # 1. 登录页面
        self.tab_login = QWidget()
        login_layout = QVBoxLayout(self.tab_login)
        form_login = QFormLayout()

        # 下拉框切换用户
        self.l_user = QComboBox()
        self.l_user.setEditable(True)
        self.l_pwd = QLineEdit()
        self.l_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.chk_remember = QCheckBox("记住密码")

        form_login.addRow("用户名:", self.l_user)
        form_login.addRow("密  码:", self.l_pwd)
        form_login.addRow("", self.chk_remember)

        # 按钮布局：登录与游客
        btn_layout = QHBoxLayout()
        self.btn_login = QPushButton("登录系统")
        self.btn_guest = QPushButton("游客看盘")
        self.btn_login.setStyleSheet("background-color: #2196F3; color: white; padding: 6px; font-weight: bold;")
        self.btn_guest.setStyleSheet("background-color: #9E9E9E; color: white; padding: 6px; font-weight: bold;")

        self.btn_login.clicked.connect(self.do_login)
        self.btn_guest.clicked.connect(self.reject)  # 游客点击触发拒绝，关闭弹窗

        btn_layout.addWidget(self.btn_login)
        btn_layout.addWidget(self.btn_guest)

        login_layout.addStretch()
        login_layout.addLayout(form_login)
        login_layout.addLayout(btn_layout)
        login_layout.addStretch()

        # 2. 注册页面
        self.tab_reg = QWidget()
        reg_layout = QVBoxLayout(self.tab_reg)
        form_reg = QFormLayout()
        self.r_user = QLineEdit()
        self.r_pwd = QLineEdit()
        self.r_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.r_pwd2 = QLineEdit()
        self.r_pwd2.setEchoMode(QLineEdit.EchoMode.Password)
        self.r_key = QLineEdit()
        self.r_key.setPlaceholderText("请输入私钥 mykey (下单必备)")

        form_reg.addRow("用户名:", self.r_user)
        form_reg.addRow("密  码:", self.r_pwd)
        form_reg.addRow("确认密码:", self.r_pwd2)
        form_reg.addRow("交易私钥:", self.r_key)

        self.btn_reg = QPushButton("注册新账户")
        self.btn_reg.setStyleSheet("background-color: #4CAF50; color: white; padding: 6px; font-weight: bold;")
        self.btn_reg.clicked.connect(self.do_register)

        reg_layout.addLayout(form_reg)
        reg_layout.addWidget(self.btn_reg)

        self.tabs.addTab(self.tab_login, "登录")
        self.tabs.addTab(self.tab_reg, "注册")
        layout.addWidget(self.tabs)

        # 加载记住的密码
        self.saved_users = {}
        self.load_saved_users()
        self.l_user.currentTextChanged.connect(self.on_user_changed)

    def load_saved_users(self):
        if os.path.exists(SAVED_USERS_FILE):
            try:
                with open(SAVED_USERS_FILE, 'r', encoding='utf-8') as f:
                    self.saved_users = json.load(f)
            except Exception:
                pass

        if self.saved_users:
            self.l_user.addItems(list(self.saved_users.keys()))
            self.l_user.setCurrentIndex(0)
            self.on_user_changed(self.l_user.currentText())

    def on_user_changed(self, username):
        if username in self.saved_users:
            self.l_pwd.setText(self.saved_users[username])
            self.chk_remember.setChecked(True)
        else:
            self.l_pwd.clear()
            self.chk_remember.setChecked(False)

    def do_login(self):
        u = self.l_user.currentText().strip()
        p = self.l_pwd.text()
        ok, mykey = verify_user(u, p)
        if ok:
            Session.username = u
            Session.mykey = mykey
            Session.is_logged_in = True

            if self.chk_remember.isChecked():
                self.saved_users[u] = p
            else:
                self.saved_users.pop(u, None)

            with open(SAVED_USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.saved_users, f)

            self.accept()
        else:
            QMessageBox.warning(self, "错误", "用户名或密码错误！")

    def do_register(self):
        u, p, p2 = self.r_user.text().strip(), self.r_pwd.text(), self.r_pwd2.text()
        k = self.r_key.text().strip()
        if not u or not p: return QMessageBox.warning(self, "错误", "账号和密码不能为空！")
        if p != p2: return QMessageBox.warning(self, "错误", "两次密码输入不一致！")
        if register_user(u, p, k):
            QMessageBox.information(self, "成功", "注册成功！请切换到登录页面。")
            self.tabs.setCurrentIndex(0)
            self.l_user.setCurrentText(u)
            self.l_pwd.clear()
        else:
            QMessageBox.warning(self, "错误", "用户名已存在！")