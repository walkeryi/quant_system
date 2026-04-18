# -*- coding: utf-8 -*-
"""
用户业务服务
"""
import os
import csv
from .models import md5_encrypt, init_users_csv, USERS_CSV


class UserService:
    """用户业务逻辑服务"""

    @staticmethod
    def verify_user(username: str, password: str) -> tuple:
        """验证用户，返回 (成功与否, mykey)"""
        init_users_csv()
        if not os.path.exists(USERS_CSV):
            return False, ""
        with open(USERS_CSV, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if row['username'] == username and row['password'] == md5_encrypt(password):
                    return True, row.get('mykey', '')
        return False, ""

    @staticmethod
    def register_user(username: str, password: str, mykey: str = "") -> bool:
        """注册新用户"""
        init_users_csv()
        if os.path.exists(USERS_CSV):
            with open(USERS_CSV, 'r', encoding='utf-8') as f:
                if username in [row['username'] for row in csv.DictReader(f)]:
                    return False
        with open(USERS_CSV, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([username, md5_encrypt(password), mykey])
        return True

    @staticmethod
    def update_user_mykey(username: str, new_mykey: str) -> bool:
        """更新用户的交易私钥"""
        init_users_csv()
        rows = []
        found = False
        with open(USERS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                if row['username'] == username:
                    row['mykey'] = new_mykey
                    found = True
                rows.append(row)
        if not found:
            return False
        with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return True

    @staticmethod
    def change_password(username: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        init_users_csv()
        rows = []
        found = False
        with open(USERS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                if row['username'] == username:
                    if row['password'] == md5_encrypt(old_password):
                        row['password'] = md5_encrypt(new_password)
                        found = True
                    else:
                        return False
                rows.append(row)
        if not found:
            return False
        with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return True

    @staticmethod
    def user_exists(username: str) -> bool:
        """检查用户是否存在"""
        init_users_csv()
        if not os.path.exists(USERS_CSV):
            return False
        with open(USERS_CSV, 'r', encoding='utf-8') as f:
            return username in [row['username'] for row in csv.DictReader(f)]
