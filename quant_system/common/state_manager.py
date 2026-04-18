# -*- coding: utf-8 -*-
# 文件路径: quant_system/common/state_manager.py
import json
import os

class StateManager:
    """模拟交易状态管理器"""
    STATE_FILE = "quant_system/cache/sim_state.json"
    HISTORY_FILE = "quant_system/cache/sim_history.json"

    @classmethod
    def _ensure_dir(cls, filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

    @classmethod
    def load_sim_state(cls):
        if not os.path.exists(cls.STATE_FILE):
            return {"is_running": False}
        try:
            with open(cls.STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"is_running": False}

    @classmethod
    def save_sim_state(cls, state_dict):
        cls._ensure_dir(cls.STATE_FILE)
        with open(cls.STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=4)

    @classmethod
    def append_sim_history(cls, state_dict):
        cls._ensure_dir(cls.HISTORY_FILE)
        history = []
        if os.path.exists(cls.HISTORY_FILE):
            with open(cls.HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        history.append(state_dict)
        with open(cls.HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)

    @classmethod
    def get_sim_history(cls):
        if not os.path.exists(cls.HISTORY_FILE):
            return []
        try:
            with open(cls.HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []