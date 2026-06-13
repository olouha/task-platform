﻿# TaskPlatform 日志查看脚本
# 实时查看后端日志

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DeployDir = $ScriptDir
while (-not (Test-Path "$DeployDir\web\backend\main.py") -and (Split-Path -Parent $DeployDir)) {
    $DeployDir = Split-Path -Parent $DeployDir
}
$LogFile = "$DeployDir\logs\backend.log"
$ErrorLogFile = "$DeployDir\logs\backend-error.log"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TaskPlatform 日志查看" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "选择要查看的日志:" -ForegroundColor Yellow
Write-Host "  1. 标准输出日志 (实时)" -ForegroundColor White
Write-Host "  2. 错误日志 (实时)" -ForegroundColor White
Write-Host "  3. 标准输出日志 (全部)" -ForegroundColor White
Write-Host "  4. 错误日志 (全部)" -ForegroundColor White
Write-Host "  5. 退出" -ForegroundColor White
Write-Host ""

$Choice = Read-Host "请选择 (1-5)"

switch ($Choice) {
    "1" {
        if (Test-Path $LogFile) {
            Write-Host "`n=== 实时标准日志 (Ctrl+C 退出) ===`n" -ForegroundColor Green
            Get-Content $LogFile -Wait -Tail 50
        } else {
            Write-Host "日志文件不存在: $LogFile" -ForegroundColor Yellow
        }
    }
    "2" {
        if (Test-Path $ErrorLogFile) {
            Write-Host "`n=== 实时错误日志 (Ctrl+C 退出) ===`n" -ForegroundColor Red
            Get-Content $ErrorLogFile -Watch -Tail 50
        } else {
            Write-Host "日志文件不存在: $ErrorLogFile" -ForegroundColor Yellow
        }
    }
    "3" {
        if (Test-Path $LogFile) {
            Write-Host "`n=== 全部标准日志 ===`n" -ForegroundColor Green
            Get-Content $LogFile | Select-Object -Last 100
        } else {
            Write-Host "日志文件不存在: $LogFile" -ForegroundColor Yellow
        }
    }
    "4" {
        if (Test-Path $ErrorLogFile) {
            Write-Host "`n=== 全部错误日志 ===`n" -ForegroundColor Red
            Get-Content $ErrorLogFile | Select-Object -Last 100
        } else {
            Write-Host "日志文件不存在: $ErrorLogFile" -ForegroundColor Yellow
        }
    }
    default {
        Write-Host "退出" -ForegroundColor Yellow
    }
}
