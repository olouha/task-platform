@echo off
REM ========================================
REM GitHub 推送脚本
REM ========================================

echo.
echo ========================================
echo GitHub 仓库推送向导
echo ========================================
echo.

cd /d "%~dp0"

REM 检查git状态
echo [1/4] 检查 Git 状态...
git status >nul 2>&1
if errorlevel 1 (
    echo [错误] 请先初始化 Git: git init
    pause
    exit /b 1
)

REM 询问仓库名称
echo.
echo [2/4] 请输入 GitHub 用户名:
set /p GH_USER=
echo.
echo 请输入仓库名称 (直接回车使用默认: task-platform):
set /p GH_REPO=
if "%GH_REPO%"=="" set GH_REPO=task-platform

echo.
echo [3/4] 配置远程仓库...
git remote remove origin 2>nul
git remote add origin https://github.com/%GH_USER%/%GH_REPO%.git

echo.
echo [4/4] 推送到 GitHub...
echo.
echo ========================================
echo.
echo 请在浏览器中创建仓库:
echo   https://github.com/new
echo.
echo 1. 仓库名称: %GH_REPO%
echo 2. 不要勾选任何选项
echo 3. 点击 "Create repository"
echo.
echo 创建完成后，回到这里按任意键继续...
echo.
pause

echo.
echo 开始推送...
git push -u origin master --force

if errorlevel 1 (
    echo.
    echo [错误] 推送失败！
    echo.
    echo 可能原因:
    echo   1. 仓库不存在
    echo   2. 用户名或仓库名错误
    echo   3. 没有权限 (需要 Personal Access Token)
    echo.
    echo 如果需要 Token，请访问:
    echo   https://github.com/settings/tokens
    echo.
    echo 创建 Token 时勾选: repo (全部)
    echo.
    echo 使用 Token 的方法:
    echo   git remote set-url origin https://TOKEN@github.com/%GH_USER%/%GH_REPO%.git
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo 推送成功！
echo ========================================
echo.
echo 接下来请在 GitHub 设置 Secrets:
echo.
echo 1. 进入仓库 -> Settings -> Secrets and variables -> Actions
echo 2. 点击 "New repository secret"
echo.
echo 添加这两个 secret:
echo   Name: MYSTEEL_USERNAME
echo   Value: M6616592358
echo.
echo   Name: MYSTEEL_PASSWORD
echo   Value: mysteel573005
echo.
echo 3. 进入 Actions 页面查看定时任务
echo.
pause