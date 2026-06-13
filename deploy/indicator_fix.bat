@echo off
REM 部署指标库本地化修复到腾讯云

echo ============================================
echo 部署指标库修复 - 腾讯云
echo ============================================

REM 设置服务器路径
set SERVER_DIR=C:\taskplatform
set SOURCE_DIR=e:\E\任务\task-platform

echo.
echo [1/3] 复制服务文件...
copy /Y "%SOURCE_DIR%\web\backend\services\local_indicator_service.py" "%SERVER_DIR%\backend\services\"
copy /Y "%SOURCE_DIR%\web\backend\services\init_indicator_data.py" "%SERVER_DIR%\backend\services\"
copy /Y "%SOURCE_DIR%\web\backend\api\indicator_report.py" "%SERVER_DIR%\backend\api\"

echo [2/3] 初始化指标库数据...
cd /d %SERVER_DIR%\backend
python services\init_indicator_data.py

echo [3/3] 重启服务...
cd /d %SERVER_DIR%
call stop.bat
timeout /t 3 /nobreak >nul
call start.bat

echo.
echo ============================================
echo 部署完成!
echo ============================================
echo.
echo 请访问: http://140.143.125.234:8080/indicator-report
echo.

pause
