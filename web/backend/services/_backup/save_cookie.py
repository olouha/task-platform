#!/usr/bin/env python3
"""
Mysteel Cookie 获取脚本
使用方法：
1. 在浏览器中登录 Mysteel (https://www.mysteel.com)
2. 打开开发者工具 (F12) -> Application -> Cookies -> www.mysteel.com
3. 复制所有Cookie，格式如: name=value; name2=value2
4. 粘贴到下方 COOKIE_STRING
5. 运行脚本
"""
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'
COOKIE_FILE = DATA_DIR / 'mysteel_cookies.json'

# 从浏览器复制的Cookie字符串（请替换为实际的Cookie）
# 格式: name=value; name2=value2; ...
COOKIE_STRING = """请从这里开始复制，到最后
name=value; name2=value2; ..."""


def parse_cookie_string(cookie_str: str) -> list:
    """解析Cookie字符串为Playwright格式"""
    cookies = []
    for part in cookie_str.split(';'):
        part = part.strip()
        if '=' in part:
            name, value = part.split('=', 1)
            cookies.append({
                'name': name.strip(),
                'value': value.strip(),
                'domain': '.mysteel.com',
                'path': '/'
            })
    return cookies


def main():
    if COOKIE_STRING.startswith('请从这里'):
        print('错误：请先替换 COOKIE_STRING 为实际的Cookie')
        print('\n获取Cookie的方法：')
        print('1. 在浏览器中登录 Mysteel')
        print('2. 打开开发者工具 (F12) -> Application -> Storage -> Cookies -> www.mysteel.com')
        print('3. 复制所有Cookie的名称和值')
        print('4. 粘贴到脚本中的 COOKIE_STRING 变量')
        return

    cookies = parse_cookie_string(COOKIE_STRING)
    print(f'解析到 {len(cookies)} 个Cookie')

    with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f'Cookie已保存到: {COOKIE_FILE}')


if __name__ == '__main__':
    main()