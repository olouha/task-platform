@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo [%date% %time%] 开始抓取数据...
python services/text_scraper.py
echo [%date% %time%] 抓取完成
