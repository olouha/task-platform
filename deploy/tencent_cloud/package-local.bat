@echo off
chcp 65001 >nul
echo ========================================
echo  本地打包脚本 - 腾讯云部署用
echo ========================================
echo.

:: 设置路径
set SOURCE_DIR=e:\E\任务\task-platform\web\backend
set TEMP_DIR=%TEMP%\task-platform-deploy
set OUTPUT_DIR=%USERPROFILE%\Desktop

:: 创建临时目录
echo [1/4] 创建临时目录...
if exist "%TEMP_DIR%" rd /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"
mkdir "%TEMP_DIR%\api"
mkdir "%TEMP_DIR%\models"
mkdir "%TEMP_DIR%\services"
echo [完成]
echo.

:: 复制文件
echo [2/4] 复制文件到临时目录...
echo   - api 文件夹...
xcopy /s /y "%SOURCE_DIR%\api\*.py" "%TEMP_DIR%\api\" >nul
echo   - models 文件夹...
xcopy /s /y "%SOURCE_DIR%\models\*.py" "%TEMP_DIR%\models\" >nul
echo   - services 文件夹...
xcopy /s /y "%SOURCE_DIR%\services\*.py" "%TEMP_DIR%\services\" >nul
echo [完成]
echo.

:: 压缩文件
echo [3/4] 压缩文件...
powershell -Command "Compress-Archive -Path '%TEMP_DIR%\api\*' -DestinationPath '%OUTPUT_DIR%\api_files.zip' -Force"
powershell -Command "Compress-Archive -Path '%TEMP_DIR%\models\*' -DestinationPath '%OUTPUT_DIR%\models_files.zip' -Force"
powershell -Command "Compress-Archive -Path '%TEMP_DIR%\services\*' -DestinationPath '%OUTPUT_DIR%\services_files.zip' -Force"
echo [完成]
echo.

:: 清理临时目录
echo [4/4] 清理临时文件...
rd /s /q "%TEMP_DIR%"
echo [完成]
echo.

:: 完成
echo ========================================
echo  打包完成！
echo ========================================
echo.
echo  请将以下文件复制到腾讯云桌面：
echo    - api_files.zip
echo    - models_files.zip
echo    - services_files.zip
echo.
dir "%OUTPUT_DIR%\api_files.zip"
dir "%OUTPUT_DIR%\models_files.zip"
dir "%OUTPUT_DIR%\services_files.zip"
echo.
pause