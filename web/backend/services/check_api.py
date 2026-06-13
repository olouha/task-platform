"""
检查价格查询页面的网络请求，找到API接口
"""
import asyncio
from playwright.async_api import async_playwright
import json
import time


async def check_network_requests():
    """监听网络请求，找到API"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
        page = await context.new_page()

        # 存储API请求
        api_requests = []

        def log_request(request):
            url = request.url
            method = request.method
            if any(keyword in url.lower() for keyword in ['api', 'query', 'search', 'price', 'data']):
                api_requests.append({
                    'url': url,
                    'method': method,
                    'headers': request.headers
                })
                print(f"[请求] {method} {url}")

        page.on('request', log_request)

        print("1. 访问价格查询页面...")
        url = 'https://price.mysteel.com/#/price-search?breedId=1-1'
        await page.goto(url, wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(5000)

        print(f"\n2. 找到 {len(api_requests)} 个可能的API请求")

        # 显示前10个
        for i, req in enumerate(api_requests[:10]):
            print(f"\n[{i}] {req['method']} {req['url'][:100]}")

        # 尝试查找GraphQL或REST API
        print("\n3. 查找API模式...")

        graphql_apis = [r for r in api_requests if 'graphql' in r['url'].lower()]
        rest_apis = [r for r in api_requests if any(kw in r['url'].lower() for kw in ['api', 'query', 'search'])]

        print(f"   GraphQL API: {len(graphql_apis)} 个")
        print(f"   REST API: {len(rest_apis)} 个")

        # 查看响应
        print("\n4. 检查响应内容...")

        async def log_response(response):
            try:
                if response.status == 200:
                    ct = response.headers.get('content-type', '')
                    if 'application/json' in ct or 'text/html' in ct:
                        url = response.url
                        if any(kw in url.lower() for kw in ['api', 'query', 'search', 'price', 'data']):
                            print(f"[响应] {url[:80]}")
                            try:
                                text = await response.text()
                                if text and len(text) < 500:
                                    print(f"       内容: {text[:200]}")
                            except:
                                pass
            except:
                pass

        page.on('response', log_response)

        # 尝试触发查询
        print("\n5. 尝试触发查询...")

        # 查找并点击查询按钮
        try:
            # 查找可能的日期输入框
            date_inputs = await page.query_selector_all('input[placeholder*="日期"], input[placeholder*="时间"], input[class*="date"]')

            if date_inputs:
                # 尝试输入一个测试日期
                await date_inputs[0].click()
                await page.wait_for_timeout(500)
                await date_inputs[0].fill('2024-01-06')
                await page.wait_for_timeout(1000)

            # 查找查询按钮
            search_buttons = await page.query_selector_all('button:has-text("查询"), button:has-text("搜索"), [class*="search"]:not(input)')
            if search_buttons:
                await search_buttons[0].click()
                await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"   查询操作失败: {e}")

        await browser.close()

        # 输出找到的API
        print("\n6. API汇总:")
        if api_requests:
            unique_urls = list(set(r['url'] for r in api_requests))
            for url in unique_urls[:15]:
                print(f"   - {url[:120]}")
        else:
            print("   未找到明显的API")


if __name__ == '__main__':
    asyncio.run(check_network_requests())
