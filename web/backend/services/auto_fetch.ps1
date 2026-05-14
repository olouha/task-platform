# 山东烟台钢筋价格自动抓取脚本
# 使用方法：
# 1. 右键点击此文件 -> 使用 PowerShell 运行
# 2. 或用 Windows 任务计划程序 设置每日定时执行

$ErrorActionPreference = "Stop"

# 设置路径
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServicesDir = Join-Path $ScriptDir "services"
$LogDir = Join-Path $ServicesDir "logs"
$LogFile = Join-Path $LogDir "auto_fetch.log"

# 确保目录存在
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force }

# 写入日志
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] $Message"
    Add-Content -Path $LogFile -Value $logEntry -Encoding UTF8
    Write-Host $logEntry
}

Write-Log "========== 开始自动抓取 =========="
Write-Log "工作目录: $ServicesDir"

# 切换到 services 目录
Set-Location $ServicesDir

# 设置 Python 环境
$PythonCmd = "python"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    $PythonCmd = "python3"
}

Write-Log "执行抓取..."

# 执行 Python 抓取脚本
$PythonScript = @"
import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, '.')
from yantai_rebar_scraper import YantaiRebarScraper, save_to_excel

def main():
    scraper = YantaiRebarScraper()

    # 检查是否今日已抓取
    can_fetch, reason = scraper._check_rate_limit()

    if not can_fetch:
        print(f'今日已抓取: {reason}')
        return True

    # 执行抓取
    result = asyncio.run(scraper.fetch_async(force=True))

    if result.success and result.prices:
        save_to_excel(result)
        print(f'抓取成功: {len(result.prices)} 条数据')

        # 更新抓取记录
        record = {
            'last_fetch': result.fetched_at,
            'success': True,
            'prices_count': len(result.prices),
            'region': '山东烟台'
        }
        with open('.logs/yantai_last_fetch.json', 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        return True
    else:
        print(f'抓取失败: {result.error_message}')
        return False

if __name__ == '__main__':
    main()
"@

try {
    $result = & $PythonCmd -c $PythonScript 2>&1
    $result | ForEach-Object { Write-Log $_ }

    if ($LASTEXITCODE -eq 0) {
        Write-Log "抓取任务完成!"
    } else {
        Write-Log "抓取出错，退出码: $LASTEXITCODE"
    }
} catch {
    Write-Log "错误: $_"
}

Write-Log "========== 抓取结束 =========="
Write-Log ""