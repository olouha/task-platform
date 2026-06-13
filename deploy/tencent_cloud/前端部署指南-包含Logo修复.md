# 腾讯云部署前端 - 包含静态文件（Logo）修复

## 问题说明
之前 logo 无法显示是因为 nginx 配置没有处理静态文件，所有请求都代理到了后端 API。

## 解决方案
需要：
1. 构建前端（生成 dist 目录）
2. 上传到服务器
3. 更新 nginx 配置支持静态文件

---

## 步骤 1: 在本地构建前端

```powershell
cd e:\E\任务\task-platform\web\frontend
npm run build
```

构建完成后，验证 `dist` 目录包含 logo 文件：
```powershell
dir e:\E\任务\task-platform\web\frontend\dist | findstr logo
```

应该看到：
- `logo.jpg`
- `ai-logo.jpg`

---

## 步骤 2: 上传到腾讯云服务器

### 方式 A: 使用远程桌面（简单）

1. 连接到腾讯云服务器（远程桌面）
2. 在本地将 `e:\E\任务\task-platform\web\frontend\dist` 目录打包成 ZIP
3. 通过远程桌面复制粘贴到服务器 `C:\taskplatform\web\frontend\`
4. 在服务器上解压

### 方式 B: 使用 PowerShell（如果已配置 WinRM）

```powershell
# 从本地上传到服务器
$server = "你的服务器IP"
$username = "Administrator"
$password = ConvertTo-SecureString "你的密码" -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential ($username, $password)

# 复制 dist 目录
Copy-Item -Path "e:\E\任务\task-platform\web\frontend\dist" `
          -Destination "\\$server\C$\taskplatform\web\frontend\" `
          -Recurse -Force
```

---

## 步骤 3: 更新服务器上的 nginx 配置

1. 登录腾讯云服务器（远程桌面）
2. 备份旧配置：
```powershell
copy C:\nginx\conf\nginx.conf C:\nginx\conf\nginx.conf.backup
```

3. 复制新配置：
```powershell
# 在服务器上执行
copy C:\taskplatform\deploy\tencent_cloud\nginx-frontend.conf C:\nginx\conf\nginx.conf /Y
```

4. 测试配置：
```powershell
C:\nginx\nginx.exe -t
```

5. 重启 nginx：
```powershell
C:\nginx\nginx.exe -s reload
```

---

## 步骤 4: 验证部署

在浏览器中访问你的服务器：

1. **首页**: `http://你的服务器IP`
2. **Logo 图片**: `http://你的服务器IP/logo.jpg`
3. **AI Logo**: `http://你的服务器IP/ai-logo.jpg`

所有都应该正常显示！

---

## 目录结构验证

服务器上的目录结构应该是：

```
C:\taskplatform\
├── web\
│   ├── backend\
│   │   └── (后端代码)
│   └── frontend\
│       └── dist\
│           ├── index.html
│           ├── assets\
│           │   ├── index-xxx.js
│           │   └── index-xxx.css
│           ├── logo.jpg          ✅
│           └── ai-logo.jpg       ✅
└── deploy\
    └── tencent_cloud\
```

---

## 故障排除

### Logo 仍然不显示？

1. **检查文件是否存在**：
```powershell
dir C:\taskplatform\web\frontend\dist\logo.jpg
dir C:\taskplatform\web\frontend\dist\ai-logo.jpg
```

2. **检查 nginx 错误日志**：
```powershell
type C:\nginx\logs\error.log
```

3. **检查 nginx 配置**：
```powershell
type C:\nginx\conf\nginx.conf | findstr "root"
```

应该看到：
```
root C:/taskplatform/web/frontend/dist;
```

4. **清除浏览器缓存**：
   - 按 `Ctrl + F5` 强制刷新
   - 或在开发者工具中禁用缓存

---

## 一键部署脚本（可选）

如果需要自动化部署，可以使用 `一键部署.bat`：

```batch
@echo off
echo 正在构建前端...
cd e:\E\任务\task-platform\web\frontend
call npm run build

echo 正在上传到服务器...
REM 添加上传逻辑

echo 正在更新 nginx 配置...
REM 添加配置更新逻辑

echo 完成！
pause
```

---

## 联系支持

如有问题，请检查：
1. Nginx 错误日志：`C:\nginx\logs\error.log`
2. 后端日志：`C:\taskplatform\logs\`
3. 浏览器开发者工具 Console 和 Network 标签
