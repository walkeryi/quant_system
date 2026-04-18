# -*- coding: utf-8 -*-
"""
交易接口服务
"""
import requests
from quant_system.config import HSA_TOKEN


class TraderAPI:
    """交易执行接口"""
    BASE_URL = "http://www.sanhulianghua.com:2008/v1"

    @classmethod
    def execute(cls, endpoint: str, code: str, price: float, hand: int, policy: str) -> dict:
        """
        :param endpoint: 交易端点
        :param code: 股票代码
        :param price: 价格
        :param hand: 手数
        :param policy: 策略名称
        """
        params = {
            'token': HSA_TOKEN,
            'code': str(code).zfill(6),
            'price': price,
            'hand': hand,
            'policy': policy,
        }
        try:
            resp = requests.get(f"{cls.BASE_URL}/{endpoint}", params=params, timeout=10)
            return resp.json()
        except Exception as e:
            return {'ret': -1, 'msg': str(e)}
