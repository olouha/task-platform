# GitHub Actions 定时抓取设置

## 简介

使用 GitHub Actions 定时抓取山东烟台钢筋价格，不依赖本地电脑。

## 设置步骤

### 1. 创建 GitHub 仓库

```bash
# 在 GitHub 上创建新仓库，然后：
cd e:/E/任务/task-platform
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/你的用户名/task-platform.git
git push -u origin main
```

### 2. 添加 secrets

在 GitHub 仓库 Settings -> Secrets and variables -> Actions 中添加：

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `MYSTEEL_USERNAME` | 我的钢铁网用户名 | `M6616592358` |
| `MYSTEEL_PASSWORD` | 我的钢铁网密码 | `mysteel573005` |

### 3. 查看执行结果

1. 进入 GitHub 仓库
2. 点击 Actions 标签
3. 可以看到定时任务的执行历史
4. 点击任意执行可以看到详细日志

## 定时规则

- **执行时间**: 每天北京时间 08:00 (UTC 00:00)
- **时区**: 使用 GitHub Actions 的 UTC 时区

## 修改定时时间

编辑 `.github/workflows/fetch-prices.yml`：

```yaml
schedule:
  - cron: '0 0 * * *'  # 每天 UTC 0:00 = 北京时间 8:00
```

常用时间对照：
- `0 0 * * *` = 每天 UTC 00:00 = 北京时间 08:00
- `0 1 * * *` = 每天 UTC 01:00 = 北京时间 09:00
- `0 8 * * *` = 每天 UTC 08:00 = 北京时间 16:00

## 手动触发

在 GitHub Actions 页面点击 "Run workflow" 可以手动触发抓取。

## 注意事项

1. GitHub Actions 免费额度：每月 2000 分钟
2. 每次执行约需 3-5 分钟
3. 数据会保存在仓库中，可以随时查看历史数据