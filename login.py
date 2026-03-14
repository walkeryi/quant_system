# login.py
import tkinter as tk
from tkinter import messagebox, ttk
import hashlib
import csv
import os
from config import USERS_CSV


def md5_encrypt(password):
    """对密码进行MD5加密"""
    return hashlib.md5(password.encode('utf-8')).hexdigest()


def init_users_csv():
    """初始化用户文件，如果不存在则创建并添加默认用户（admin/123456）"""
    if not os.path.exists(USERS_CSV):
        with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['username', 'password'])  # 写入表头
            # 添加默认用户 admin, 密码 123456 (加密后存储)
            default_pwd = md5_encrypt('123456')
            writer.writerow(['admin', default_pwd])


def verify_user(username, password):
    """验证用户名和密码是否正确"""
    if not os.path.exists(USERS_CSV):
        return False
    with open(USERS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['username'] == username:
                # 对比加密后的密码
                return row['password'] == md5_encrypt(password)
    return False


def register_user(username, password):
    """注册新用户，写入CSV"""
    # 检查用户名是否已存在
    if os.path.exists(USERS_CSV):
        with open(USERS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['username'] == username:
                    return False  # 用户名已存在
    # 写入新用户
    with open(USERS_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([username, md5_encrypt(password)])
    return True


class LoginWindow:
    def __init__(self, on_login_success):
        self.on_login_success = on_login_success  # 登录成功后的回调函数
        self.window = tk.Tk()
        self.window.title("用户登录")
        self.window.geometry("300x200")
        self.window.resizable(False, False)

        # 初始化用户文件
        init_users_csv()

        self.create_widgets()

    def create_widgets(self):
        # 用户名
        tk.Label(self.window, text="用户名:").place(x=50, y=40)
        self.username_entry = tk.Entry(self.window)
        self.username_entry.place(x=120, y=40)

        # 密码
        tk.Label(self.window, text="密码:").place(x=50, y=80)
        self.password_entry = tk.Entry(self.window, show="*")
        self.password_entry.place(x=120, y=80)

        # 登录按钮
        self.login_btn = tk.Button(self.window, text="登录", command=self.login)
        self.login_btn.place(x=80, y=130)

        # 注册按钮
        self.register_btn = tk.Button(self.window, text="注册", command=self.register)
        self.register_btn.place(x=160, y=130)

        # 状态标签
        self.status_label = tk.Label(self.window, text="", fg="red")
        self.status_label.place(x=50, y=170)

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            self.status_label.config(text="用户名和密码不能为空")
            return

        if verify_user(username, password):
            self.status_label.config(text="登录成功！", fg="green")
            self.window.after(500, self.close_and_success)  # 延迟关闭，让用户看到成功提示
        else:
            self.status_label.config(text="用户名或密码错误", fg="red")

    def register(self):
        """弹出注册窗口"""
        reg_win = tk.Toplevel(self.window)
        reg_win.title("注册新用户")
        reg_win.geometry("300x200")
        reg_win.resizable(False, False)

        tk.Label(reg_win, text="用户名:").place(x=50, y=40)
        reg_username = tk.Entry(reg_win)
        reg_username.place(x=120, y=40)

        tk.Label(reg_win, text="密码:").place(x=50, y=80)
        reg_password = tk.Entry(reg_win, show="*")
        reg_password.place(x=120, y=80)

        tk.Label(reg_win, text="确认密码:").place(x=40, y=120)
        reg_confirm = tk.Entry(reg_win, show="*")
        reg_confirm.place(x=120, y=120)

        def do_register():
            uname = reg_username.get().strip()
            pwd = reg_password.get()
            confirm = reg_confirm.get()

            if not uname or not pwd:
                messagebox.showerror("错误", "用户名和密码不能为空")
                return
            if pwd != confirm:
                messagebox.showerror("错误", "两次密码输入不一致")
                return
            if len(pwd) < 3:
                messagebox.showerror("错误", "密码至少3位")
                return

            if register_user(uname, pwd):
                messagebox.showinfo("成功", "注册成功，请登录")
                reg_win.destroy()
            else:
                messagebox.showerror("错误", "用户名已存在")

        tk.Button(reg_win, text="注册", command=do_register).place(x=120, y=160)

    def close_and_success(self):
        """关闭登录窗口并调用成功回调"""
        self.window.destroy()
        self.on_login_success()

    def run(self):
        self.window.mainloop()