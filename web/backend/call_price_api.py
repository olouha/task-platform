# -*- coding: utf-8 -*-
import requests
import re
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 调用旗舰商家推荐API获取价格
url = 'https://e.mysteel.com/api/shop/flagship/queryFlagshipSpotHq'
params = {
    'breedId': '010101',  # 螺纹钢
    'areaCode': '01010205',  # 烟台
    'areaName': '烟台'
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://jiancai.mysteel.com/',
}

print('=== 旗舰商家价格 ===\n')

try:
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    data = resp.json()

    if data.get('code') == 200:
        items = data.get('data', [])
        print(f'找到 {len(items)} 条价格\n')

        for item in items:
            resource = item.get('resourceName', '')
            price = item.get('taxPrice', '')
            unit = item.get('taxPriceUnit', '')
            company = item.get('companyName', '')

            print(f'品种: {resource}')
            print(f'价格: {price} {unit}')
            print(f'商家: {company}')
            print('---')
    else:
        print(f'API错误: {data}')

except Exception as e:
    print(f'请求失败: {e}')

# 调用均价API
print('\n\n=== 市场均价 ===\n')

avg_url = 'https://api.mysteel.com/publishd/information/listMarketAvg'
avg_params = {
    'typeIds': '228',
    'avgType': '1',
    'size': '10',
    'breedIds': '010101',
    'relationType': '0',
    'relationIds': '01010205'
}

try:
    resp = requests.get(avg_url, params=avg_params, headers=headers, timeout=30)
    print(f'均价API响应: {resp.text[:1000]}...')

except Exception as e:
    print(f'均价API失败: {e}')
