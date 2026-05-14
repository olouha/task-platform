"""
部署到 Railway 的脚本
Railway 提供免费定时任务和 PostgreSQL
"""

import subprocess
import os
import sys

def deploy_to_railway():
    """部署到 Railway"""

    print("=" * 60)
    print("  TaskPlatform 部署到 Railway")
    print("=" * 60)
    print()

    # 1. 检查 Railway CLI
    print("[1/4] 检查 Railway CLI...")
    try:
        result = subprocess.run(['railway', '--version'], capture_output=True, text=True)
        print(f"   ✅ {result.stdout.strip()}")
    except FileNotFoundError:
        print("   ❌ 未安装 Railway CLI")
        print("   请运行: npm i -g @railway/cli")
        return False

    # 2. 登录
    print("\n[2/4] 登录 Railway...")
    subprocess.run(['railway', 'login'])

    # 3. 初始化项目
    print("\n[3/4] 初始化 Railway 项目...")
    os.chdir('web/backend')

    try:
        subprocess.run(['railway', 'init'], check=False)
    except:
        print("   ⚠️  请手动选择项目或跳过")

    # 4. 部署
    print("\n[4/4] 部署中...")
    print("   设置环境变量:")
    print("   - SUPABASE_URL = 你的Supabase项目URL")
    print("   - SUPABASE_KEY = 你的Supabase API Key")
    print()
    print("   设置定时任务:")
    print("   - 每天早上8点自动抓取价格")
    print()

    subprocess.run(['railway', 'up'])

    print("\n✅ 部署完成!")
    print("\n查看日志: railway logs")
    print("配置定时: railway variables")

    return True


def deploy_to_cloudflare():
    """部署到 Cloudflare Workers"""

    print("=" * 60)
    print("  TaskPlatform 部署到 Cloudflare Workers")
    print("=" * 60)
    print()

    # 1. 检查 Wrangler CLI
    print("[1/4] 检查 Wrangler CLI...")
    try:
        result = subprocess.run(['wrangler', '--version'], capture_output=True, text=True)
        print(f"   ✅ {result.stdout.strip()}")
    except FileNotFoundError:
        print("   ❌ 未安装 Wrangler CLI")
        print("   请运行: npm i -g wrangler")
        return False

    # 2. 登录
    print("\n[2/4] 登录 Cloudflare...")
    subprocess.run(['wrangler', 'login'])

    # 3. 配置
    print("\n[3/4] 配置环境变量...")
    print("   设置 SUPABASE_URL 和 SUPABASE_KEY")

    # 4. 部署
    print("\n[4/4] 部署中...")
    os.chdir('web/backend')
    subprocess.run(['wrangler', 'deploy'])

    print("\n✅ 部署完成!")
    print("   定时任务: 每天早上8点自动执行")


if __name__ == '__main__':
    print()
    print("选择部署平台:")
    print("1. Railway (推荐，简单支持定时任务)")
    print("2. Cloudflare Workers (免费，需手动配置)")
    print()

    choice = input("请选择 (1/2): ").strip()

    if choice == '1':
        deploy_to_railway()
    elif choice == '2':
        deploy_to_cloudflare()
    else:
        print("无效选择")