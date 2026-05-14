@echo off
REM 山东烟台钢筋价格自动抓取
REM 使用 Windows 任务计划程序定时执行

cd /d "%~dp0"
cd services

REM 记录日志
echo [%date% %time%] 开始抓取钢筋价格... >> ..\logs\cron.log

REM 设置 Python 环境
python -c "import asyncio; import sys; sys.path.insert(0, '.'); from yantai_rebar_scraper import YantaiRebarScraper, save_to_excel; scraper = YantaiRebarScraper(); result = asyncio.run(scraper.fetch_async(force=True)); print(f'抓取结果: success={result.success}, count={len(result.prices)}')" >> ..\logs\cron.log 2>&1

echo [%date% %time%] 抓取完成 >> ..\logs\cron.log
echo 抓取任务已执行