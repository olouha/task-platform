# 价格监控API修复 - 部署说明

## 问题描述
服务器配置了 Supabase，但连接失败导致 `/api/yantai-rebar/*` API 返回 500 错误，价格监控页面显示无数据。

## 修复内容
为 `web/backend/api/yantai_db.py` 的所有 Supabase 调用添加错误处理，Supabase 失败时自动回退到 SQLite。

## 手动部署步骤

### 方式1：直接复制文件（推荐）

1. 在服务器上打开文件管理器
2. 导航到：`C:\taskplatform\web\backend\api\`
3. 备份原文件：复制 `yantai_db.py` 为 `yantai_db.py.backup`
4. 从本机复制修复后的文件到服务器
   - 本机文件：`e:\E\任务\task-platform\web\backend\api\yantai_db.py`
   - 服务器位置：`C:\taskplatform\web\backend\api\yantai_db.py`

### 方式2：使用 PowerShell 远程复制

```powershell
# 在服务器上运行
Copy-Item "\\你的本机IP\共享文件夹\task-platform\web\backend\api\yantai_db.py" "C:\taskplatform\web\backend\api\yantai_db.py" -Force
```

### 方式3：从 GitHub 拉取（如果网络正常）

```bash
cd C:\taskplatform
git pull origin main
```

## 重启后端服务

复制文件后，重启后端服务：

```powershell
# 方式1：使用重启脚本
C:\taskplatform\deploy\tencent_cloud\restart.ps1

# 方式2：手动重启
cd C:\taskplatform
taskkill /F /IM python.exe
python -m uvicorn web.backend.main:app --host 0.0.0.0 --port 8000
```

## 验证修复

1. 访问价格监控页面：http://140.143.125.234/
2. 应该能看到数据：
   - 历史数据总量：10764 条记录
   - 覆盖 415 个交易日
   - 日期范围：2024-01-02 ~ 2026-05-30

3. 检查 API 端点：
   - http://140.143.125.234/api/yantai-rebar/stats
   - http://140.143.125.234/api/yantai-rebar/latest?limit=5

## 检查日志

查看后端日志确认 Supabase 回退到 SQLite：

```powershell
# 查看最新日志
Get-Content C:\taskplatform\web\backend\services\logs\scheduler.log -Tail 50
```

应该看到类似日志：
```
[get_rebar_stats] Supabase查询失败，回退SQLite | ...
[get_rebar_stats] SQLite | total=10764
```

## 修复文件位置

修复后的文件已保存到：
- `e:\E\任务\task-platform\web\backend\api\yantai_db.py`
- `e:\E\任务\task-platform\deploy\tencent_cloud\deploy-yantai-fix.ps1`

## 数据库信息

- **数据库文件**：`C:\taskplatform\web\backend\services\data\yantai_rebar.db`
- **总记录数**：10764 条
- **日期数**：415 天
- **日期范围**：2024-01-02 ~ 2026-05-30
- **材料类型**：高线、螺纹钢、盘螺、圆钢
