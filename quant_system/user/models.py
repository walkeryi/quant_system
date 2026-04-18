# -*- coding: utf-8 -*-
"""
用户会话模型 - 从 login.py 转发，保持旧代码兼容
"""
from quant_system.login import Session
from quant_system.login import md5_encrypt, init_users_csv, SAVED_USERS_FILE
from quant_system.config import USERS_CSV

UserSession = Session

__all__ = ['Session', 'UserSession', 'md5_encrypt', 'init_users_csv', 'SAVED_USERS_FILE', 'USERS_CSV']
