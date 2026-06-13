# TaskPlatform 蓝绿部署脚本 (Windows PowerShell)
# 实现不停服更新
#
# 使用方法:
#   .\blue-green-deploy.ps1          # 正常部署
#   .\blue-green-deploy.ps1 -Verify  # 仅验证
#   .\blue-green-deploy.ps1 -Rollback # 回滚

param(
    [string]$Action = "deploy"
)

$ErrorActionPreference = "Stop"

# 颜色定义
function Write-Step { param($msg) Write-Host "[$($msg)]" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[$msg] ✓" -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host "[$msg] ⚠" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "[$msg] ✗" -ForegroundColor Red }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TaskPlatform 蓝绿部署脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 配置
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DeployDir = $ScriptDir
while (-not (Test-Path "$DeployDir\web\backend\main.py") -and (Split-Path -Parent $DeployDir)) {
    $DeployDir = Split-Path -Parent $DeployDir
}
$BackendDir = "$DeployDir\web\backend"
$LogDir = "$DeployDir\logs"
$PidDir = "$DeployDir\pids"

# 端口配置
$CurrentPort = 8000
$NewPort = 8001

Write-Host "项目目录: $DeployDir" -ForegroundColor Gray
Write-Host "后端目录: $BackendDir" -ForegroundColor Gray
Write-Host ""

# 确保目录存在
$null = New-Item -Path $LogDir -ItemType Directory -Force -ErrorAction SilentlyContinue
$null = New-Item -Path $PidDir -ItemType Directory -Force -ErrorAction SilentlyContinue

# ============================================================
# 1. 备份当前版本
# ============================================================
function Backup-Current {
    Write-Step "备份当前版本"

    $BackupDir = "$DeployDir\backups\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    $null = New-Item -Path $BackupDir -ItemType Directory -Force

    # 备份关键文件
    $BackupFiles = @(
        "$BackendDir\.env",
        "$BackendDir\services\data\*.db",
        "$BackendDir\services\data\*.json"
    )

    foreach ($pattern in $BackupFiles) {
        Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue | ForEach-Object {
            Copy-Item $_.FullName -Destination "$BackupDir\" -Force
            Write-Host "  备份: $($_.Name)" -ForegroundColor Gray
        }
    }

    # 备份整个app目录（代码）
    Copy-Item "$BackendDir" -Destination "$BackupDir\app_backup" -Recurse -Force
    Write-Success "备份完成: $BackupDir"

    return $BackupDir
}

# ============================================================
# 2. 部署新版本
# ============================================================
function Deploy-NewVersion {
    Write-Step "部署新版本"

    # 查找新代码位置
    $NewCodePaths = @(
        "$DeployDir\web\backend",      # 本地开发
        "$DeployDir\web",             # 可能是web目录
        "$DeployDir"                 # 可能是根目录
    )

    $SourceDir = $null
    foreach ($path in $NewCodePaths) {
        if (Test-Path "$path\main.py") {
            $SourceDir = $path
            break
        }
    }

    if (-not $SourceDir) {
        Write-Error "未找到新版本代码，请确保 web/backend/main.py 存在"
        return $false
    }

    Write-Host "  新代码位置: $SourceDir" -ForegroundColor Gray

    # 复制到后端目录
    $Exclude = @("__pycache__", "*.pyc", ".git", "node_modules", "data", ".env")
    $Files = Get-ChildItem -Path $SourceDir -Recurse -File | Where-Object {
        $skip = $false
        foreach ($ex in $Exclude) {
            if ($_.FullName -like "*$ex*") { $skip = $true; break }
        }
        -not $skip
    }

    foreach ($file in $Files) {
        $relativePath = $file.FullName.Substring($SourceDir.Length)
        $targetPath = "$BackendDir$relativePath"
        $targetDir = Split-Path -Parent $targetPath

        if (-not (Test-Path $targetDir)) {
            $null = New-Item -Path $targetDir -ItemType Directory -Force
        }

        Copy-Item $file.FullName -Destination $targetPath -Force
    }

    Write-Success "新版本已部署"
    return $true
}

# ============================================================
# 3. 启动新版本
# ============================================================
function Start-NewVersion {
    param($Port)

    Write-Step "启动新版本服务 (端口 $Port)"

    # 检查端口是否被占用
    $portInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($portInUse) {
        Write-Warning "端口 $Port 已被占用，尝试关闭占用进程..."
        $pids = $portInUse.OwningProcess | Sort-Object -Unique
        foreach ($pid in $pids) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
    }

    # 启动新进程
    $LogFile = "$LogDir\backend_$Port.log"
    $ErrorLogFile = "$LogDir\backend_$Port-error.log"

    $Process = Start-Process -FilePath python `
        -ArgumentList "-m uvicorn main:app --host 0.0.0.0 --port $Port --log-level info" `
        -WorkingDirectory $BackendDir `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError $ErrorLogFile `
        -WindowStyle Hidden `
        -PassThru

    # 保存PID
    $Process.Id | Out-File -FilePath "$PidDir\backend_$Port.pid" -Encoding UTF8

    # 等待启动
    Write-Host "  等待服务启动..." -ForegroundColor Gray
    Start-Sleep -Seconds 5

    # 检查进程
    $runningProcess = Get-Process -Id $Process.Id -ErrorAction SilentlyContinue
    if ($runningProcess) {
        Write-Success "新版本已启动 (PID: $($Process.Id))"
        return $true
    } else {
        Write-Error "新版本启动失败，查看日志: $ErrorLogFile"
        return $false
    }
}

# ============================================================
# 4. 验证新版本
# ============================================================
function Test-NewVersion {
    param($Port)

    Write-Step "验证新版本健康状态"

    $maxRetries = 10
    $retry = 0

    while ($retry -lt $maxRetries) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$Port/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Success "健康检查通过"
                return $true
            }
        } catch {
            # 忽略错误，继续重试
        }

        $retry++
        Write-Host "  等待健康检查... ($retry/$maxRetries)" -ForegroundColor Gray
        Start-Sleep -Seconds 3
    }

    Write-Error "健康检查超时"
    return $false
}

# ============================================================
# 5. 停止旧版本
# ============================================================
function Stop-OldVersion {
    param($Port)

    Write-Step "停止旧版本 (端口 $Port)"

    $pidFile = "$PidDir\backend_$Port.pid"

    if (Test-Path $pidFile) {
        $oldPid = Get-Content $pidFile -ErrorAction SilentlyContinue
        if ($oldPid) {
            Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
            Write-Success "旧版本已停止 (PID: $oldPid)"
        }
        Remove-Item $pidFile -ErrorAction SilentlyContinue
    }

    # 确保端口释放
    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}

# ============================================================
# 6. 切换端口
# ============================================================
function Switch-Nginx {
    Write-Step "切换 nginx 配置"

    $nginxConf = "$DeployDir\deploy\tencent_cloud\nginx-windows.conf"

    if (Test-Path $nginxConf) {
        # 备份原配置
        Copy-Item $nginxConf "$nginxConf.bak" -Force

        # 重新加载nginx
        $nginxExe = "C:\nginx\nginx.exe"
        if (Test-Path $nginxExe) {
            & $nginxExe -s reload 2>$null
            Write-Success "nginx 已重新加载"
        }
    }
}

# ============================================================
# 7. 回滚
# ============================================================
function Rollback-Version {
    Write-Step "回滚到旧版本"

    # 停止当前版本
    $currentPidFile = "$PidDir\backend_$NewPort.pid"
    if (Test-Path $currentPidFile) {
        $currentPid = Get-Content $currentPidFile -ErrorAction SilentlyContinue
        Stop-Process -Id $currentPid -Force -ErrorAction SilentlyContinue
    }

    # 启动旧版本（使用原来的端口）
    Start-NewVersion -Port $CurrentPort | Out-Null

    # 等待旧版本启动
    Start-Sleep -Seconds 5

    # 验证
    if (Test-NewVersion -Port $CurrentPort) {
        Write-Success "回滚完成"
    } else {
        Write-Error "回滚失败，请手动检查"
    }
}

# ============================================================
# 主流程
# ============================================================
switch ($Action.ToLower()) {
    "rollback" {
        Rollback-Version
    }
    "verify" {
        # 验证当前运行的版本
        Write-Step "验证当前版本"
        $currentPidFile = "$PidDir\backend_$CurrentPort.pid"
        if (Test-Path $currentPidFile) {
            $pid = Get-Content $currentPidFile
            Write-Host "  当前运行版本 PID: $pid" -ForegroundColor Gray
        }
        Test-NewVersion -Port $CurrentPort
    }
    default {
        # 正常部署流程
        try {
            # 1. 备份
            $backupDir = Backup-Current

            # 2. 部署新版本
            if (-not (Deploy-NewVersion)) {
                throw "部署失败"
            }

            # 3. 启动新版本（使用新端口）
            if (-not (Start-NewVersion -Port $NewPort)) {
                throw "启动失败"
            }

            # 4. 验证
            if (-not (Test-NewVersion -Port $NewPort)) {
                throw "验证失败"
            }

            # 5. 提示用户确认
            Write-Host ""
            Write-Host "========================================" -ForegroundColor Yellow
            Write-Host "  新版本已启动，请验证功能是否正常" -ForegroundColor Yellow
            Write-Host "========================================" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "验证地址: http://localhost:$NewPort/health" -ForegroundColor Gray
            Write-Host "API文档:  http://localhost:$NewPort/docs" -ForegroundColor Gray
            Write-Host ""

            $confirm = Read-Host "确认切换到新版本? (y/n)"

            if ($confirm -eq "y" -or $confirm -eq "Y") {
                # 停止旧版本
                Stop-OldVersion -Port $CurrentPort

                # 更新PID文件
                $newPid = Get-Content "$PidDir\backend_$NewPort.pid"
                $newPid | Out-File "$PidDir\backend_$CurrentPort.pid" -Encoding UTF8

                Write-Success "切换完成！新版本正在运行"
                Write-Host ""
                Write-Host "访问地址: http://localhost:$CurrentPort" -ForegroundColor Cyan
            } else {
                Write-Host "已取消切换，新版本仍在后台运行" -ForegroundColor Yellow
                Write-Host "如需停止新版本，请手动运行: Stop-Process -Id (Get-Content $PidDir\backend_$NewPort.pid)" -ForegroundColor Gray
            }

        } catch {
            Write-Error "部署失败: $_"
            Write-Host ""
            Write-Host "如需回滚，请运行: .\blue-green-deploy.ps1 -Rollback" -ForegroundColor Yellow
            exit 1
        }
    }
}

Write-Host ""
