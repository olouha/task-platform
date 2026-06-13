"""
测试价格查询API
"""
import asyncio
import httpx
import json
from datetime import datetime


async def test_api():
    """测试价格查询API"""
    base_url = "https://price.mysteel.com/avgprice/api/jgzx"

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("1. 获取日期范围...")
        try:
            resp = await client.get(f"{base_url}/condition/getBreedDateRange", params={"breedId": "1-1"})
            print(f"   状态: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"   响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        except Exception as e:
            print(f"   错误: {e}")

        print("\n2. 获取菜单...")
        try:
            resp = await client.get(f"{base_url}/condition/menus")
            print(f"   状态: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"   响应: {json.dumps(data, ensure_ascii=False, indent=2)[:1000]}")
        except Exception as e:
            print(f"   错误: {e}")

        print("\n3. 获取条件...")
        try:
            resp = await client.post(f"{base_url}/condition/conditions")
            print(f"   状态: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"   响应: {json.dumps(data, ensure_ascii=False, indent=2)[:1000]}")
        except Exception as e:
            print(f"   错误: {e}")

        # 尝试查询特定日期
        print("\n4. 查询特定日期的价格...")
        try:
            params = {
                "breedId": "1-1",
                "date": "2024-01-06",
                "province": "山东省",
                "city": "烟台市"
            }
            resp = await client.get(f"{base_url}/query", params=params)
            print(f"   状态: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"   响应: {json.dumps(data, ensure_ascii=False, indent=2)[:1000]}")
        except Exception as e:
            print(f"   错误: {e}")

        # 尝试另一种查询方式
        print("\n5. 尝试POST查询...")
        try:
            data = {
                "breedId": "1-1",
                "condition": {
                    "date": "2024-01-06",
                    "province": "山东省",
                    "city": "烟台市"
                },
                "pageNum": 1,
                "pageSize": 50
            }
            resp = await client.post(f"{base_url}/list", json=data)
            print(f"   状态: {resp.status_code}")
            if resp.status_code == 200:
                result = resp.json()
                print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=2)[:1000]}")
        except Exception as e:
            print(f"   错误: {e}")


if __name__ == '__main__':
    asyncio.run(test_api())
