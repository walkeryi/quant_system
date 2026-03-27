# quant_system/test_api.py
import requests
import pandas as pd
from config import HSA_TOKEN


def diagnose_kline_api(period_name, url, code="000002"):
    print(f"\n{'=' * 50}")
    print(f"🚀 开始诊断【{period_name}】接口")
    print(f"{'=' * 50}")

    params = {
        'token': HSA_TOKEN,
        'code': code,
        'all': 0  # 严格测试：0 获取最新 100 笔
    }

    print(f"请求地址: {url}")
    print(f"请求参数: {params}")

    try:
        resp = requests.get(url, params=params, timeout=10)
        print(f"HTTP 状态码: {resp.status_code}")

        data = resp.json()
        ret_code = data.get('ret')
        msg = data.get('msg')

        print(f"服务端返回码 (ret): {ret_code}")
        print(f"服务端提示语 (msg): {msg}")

        if ret_code != 200:
            print(f"❌ 错误：服务端明确拒绝了请求！原因：{msg}")
            return

        records = data.get('data', [])
        print(f"获取到的数据条数 (len): {len(records)}")

        if not records:
            print(f"⚠️ 致命发现：接口返回了 ret=200 成功，但是 data 列表是空的 []！")
            print(f"⚠️ 结论：服务端的 all=0 参数存在 Bug，或者该股票在此接口确实没有数据。")
            return

        print(f"✅ 成功获取数据！第一条数据原貌如下：\n{records[0]}")

        # 测试 Pandas 解析
        df = pd.DataFrame(records)
        print(f"\n📊 Pandas 解析出的原始列名: {df.columns.tolist()}")

    except Exception as e:
        print(f"❌ 发生意外崩溃: {e}")


if __name__ == "__main__":
    test_code = "000004"  # 使用刚才日志里没出数据的股票
    print(f"当前测试股票代码: {test_code}")

    # 1. 诊断周线
    diagnose_kline_api("周线", "http://www.sanhulianghua.com:2008/v1/hsa_zhouxian", test_code)

    # 2. 诊断月线
    diagnose_kline_api("月线", "http://www.sanhulianghua.com:2008/v1/hsa_yuexian", test_code)