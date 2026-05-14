# GitHub 推送指南

由于网络原因无法自动完成，请按以下步骤手动操作：

---

## 第一步：创建 GitHub 仓库

1. 打开浏览器，访问：https://github.com/new

2. 填写信息：
   - **Repository name**: `task-platform`
   - **Description**: `工程调差计算系统`
   - **Private/Public**: 选择 Private（私有）或 Public（公开）
   - **不要勾选** "Add a README file"
   - **不要勾选** 其他任何选项

3. 点击 **"Create repository"**

4. 创建成功后，页面会显示仓库地址，例如：
   `https://github.com/你的用户名/task-platform`

---

## 第二步：推送代码

在项目目录下打开命令提示符（CMD），运行以下命令：

```bash
cd e:\E\任务\task-platform

git remote add origin https://github.com/你的用户名/task-platform.git

git add .

git commit -m "feat: 添加 GitHub Actions 定时抓取钢筋价格"

git push -u origin master
```

---

## 第三步：设置 Secrets

1. 进入你的 GitHub 仓库
2. 点击 **Settings**（设置）
3. 左侧菜单找到 **Secrets and variables** → **Actions**
4. 点击 **"New repository secret"**

添加两个 secret：

| Name | Value |
|------|-------|
| `MYSTEEL_USERNAME` | `M6616592358` |
| `MYSTEEL_PASSWORD` | `mysteel573005` |

---

## 第四步：验证

1. 进入仓库 → **Actions** 页面
2. 可以看到 "钢筋价格定时抓取" 工作流
3. 点击 "Run workflow" 可以手动触发一次测试

---

## 完成！

设置成功后，每天北京时间 08:00 就会自动抓取钢筋价格。

---

## 常见问题

### 推送时需要登录？
创建 Personal Access Token：
1. GitHub → Settings → Developer settings → Personal access tokens
2. 点击 "Generate new token (classic)"
3. 勾选 **repo**（全部）
4. 生成后，push 时输入这个 token 作为密码

### 查看定时任务状态？
进入仓库 → Actions → 选择 "钢筋价格定时抓取"

---

如果遇到问题，随时告诉我！