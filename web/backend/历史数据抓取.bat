@echo off
chcp 65001 >nul
echo ================================================================================
echo 烟台钢筋价格历史数据抓取工具 v2.0
echo ================================================================================
echo.

cd /d "%~dp0web\backend"

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未安装Python
    pause
    exit /b 1
)

REM 检查playwright
python -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo 正在安装 playwright...
    pip install playwright
    playwright install chromium
)

echo.
echo 请选择操作:
echo   1. 首次使用 - 手动登录并保存Cookie
echo   2. 更新登录凭据
echo   3. 开始抓取 (2024-01-01 至 2026-06-10)
echo   4. 自定义日期抓取
echo   5. 检查数据完整性
echo.

set /p choice="请输入选项 (1-5): "

if "%choice%"=="1" (
    echo.
    echo ========================================
    echo 手动登录模式
    echo ========================================
    echo.
    echo 浏览器将打开登录页面，请完成登录操作
    echo 登录成功后Cookie将自动保存
    echo.
    pause
    python services/fetch_history_enhanced.py --login-only
) else if "%choice%"=="2" (
    echo.
    echo ========================================
    echo 更新登录凭据
    echo ========================================
    echo.
    python services/fetch_history_enhanced.py --update-credentials
) else if "%choice%"=="3" (
    echo.
    echo ========================================
    echo 开始抓取历史数据
    echo ========================================
    echo.
    echo 日期范围: 2024-01-01 至 2026-06-10
    echo 最小数据量: 每天11条
    echo 抓取间隔: 5秒
    echo.
    set /p confirm="确认开始抓取? (Y/N): "
    if /i "%confirm%"=="Y" (
        echo.
        echo 开始抓取...
        python services/fetch_history_enhanced.py --start 2024-01-01 --end 2026-06-10 --interval 5
    )
) else if "%choice%"=="4" (
    echo.
    echo ========================================
    echo 自定义日期抓取
    echo ========================================
    echo.
    set /p start_date="开始日期 (YYYY-MM-DD, 如 2024-01-01): "
    set /p end_date="结束日期 (YYYY-MM-DD, 如 2026-06-10): "
    set /p interval="抓取间隔秒数 (默认5): "
    echo.
    echo 日期范围: %start_date% 至 %end_date%
    echo 抓取间隔: %interval%秒
    echo.
    set /p confirm="确认开始抓取? (Y/N): "
    if /i "%confirm%"=="Y" (
        echo.
        echo 开始抓取...
        python services/fetch_history_enhanced.py --start %start_date% --end %end_date% --interval %interval%
    )
) else if "%choice%"=="5" (
    echo.
    echo ========================================
    echo 检查数据完整性
    echo ========================================
    echo.
    python -c "import sqlite3; conn = sqlite3.connect('services/data/yantai_rebar.db'); c = conn.cursor(); c.execute('SELECT date, COUNT(*) as cnt FROM rebar_prices GROUP BY date HAVING cnt < 22 ORDER BY date'); missing = c.fetchall(); print(f'数据不足的日期: {len(missing)} 天'); [print(f'  {row[0]}: {row[1]} 条') for row in missing[:20]]; conn.close()"
) else (
    echo 无效选项
)

echo.
echo ========================================
echo 操作完成
echo ========================================
echo.
echo 数据文件位置:
echo   数据库: services\data\yantai_rebar.db
echo   Excel: services\data\烟台钢筋价格_完整历史_2024_2026.xlsx
echo   日志: services\data\fetch_history_enhanced.log
echo.
pause
