# data_preprocessing/trader.py
import requests
import logging
from quant_system.config import HSA_TOKEN
from quant_system.login import Session

logger = logging.getLogger('quant_system')


class TraderAPI:
    BASE_URL = "http://www.sanhulianghua.com:2008/v1"

    @classmethod
    def execute(cls, endpoint: str, code: str, price: float, hand: int, policy: str = ""):
        mykey = Session.mykey
        if not mykey:
            return {"ret": 314, "msg": "当前账号未配置交易私钥(mykey)，请重新注册并配置！"}

        url = f"{cls.BASE_URL}/{endpoint}"
        # 价格转换，将元转为 0.1分 (例如 1.12 元 -> 1120)
        # 用 round 避免精度丢失 (如 1.12*1000 变成 1119.999)
        price_uint = int(round(float(price) * 1000))

        params = {
            'token': HSA_TOKEN,
            'mykey': mykey,
            'code': code,
            'price': price_uint,
            'hand': int(hand)
        }
        if policy:
            params['policy'] = policy

        try:
            logger.info(f"发送交易订单: {url} 参数={params}")
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"交易响应: {data}")
            return data
        except Exception as e:
            logger.exception("交易API请求异常")
            return {"ret": 500, "msg": str(e)}