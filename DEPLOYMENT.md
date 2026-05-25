# 腾讯云部署指南

## 一、准备工作

### 1.1 腾讯云服务器配置
- **轻量应用服务器**（推荐）
- **配置建议**：2核4GB（30天试用足够）
- **操作系统**：Ubuntu 22.04 或 Debian 11

### 1.2 本地准备
```bash
# 上传代码到GitHub
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin 你的仓库地址
git push -u origin main
```

---

## 二、部署步骤

### 方式一：自动部署脚本（推荐）

#### 1. 登录服务器
```bash
# 使用腾讯云提供的SSH命令或
ssh root@你的服务器IP
```

#### 2. 下载并运行部署脚本
```bash
# 下载脚本
wget https://raw.githubusercontent.com/你的仓库/main/deploy.sh
chmod +x deploy.sh

# 运行部署
./deploy.sh
```

### 方式二：手动部署

#### 1. 安装系统依赖
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nodejs npm nginx git supervisor

# CentOS
sudo yum install -y python3 python3-pip nodejs npm nginx git supervisor
```

#### 2. 克隆代码
```bash
cd /opt
git clone 你的仓库地址 taskplatform
cd taskplatform
```

#### 3. 设置后端
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
cd web/backend
pip install fastapi uvicorn[standard] openpyxl pandas

# 安装Playwright浏览器（如果需要）
pip install playwright
playwright install chromium
```

#### 4. 构建前端
```bash
cd ../frontend
npm install
npm run build
```

#### 5. 配置Nginx
```bash
sudo tee /etc/nginx/sites-available/taskplatform > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        root /opt/taskplatform/web/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/taskplatform /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 6. 配置Supervisor（进程守护）
```bash
sudo tee /etc/supervisor/conf.d/taskplatform.conf > /dev/null << 'EOF'
[program:taskplatform-backend]
command=/opt/taskplatform/venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
directory=/opt/taskplatform/web/backend
user=root
autostart=true
autorestart=true
stdout_logfile=/opt/taskplatform/logs/backend.log
EOF

sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start taskplatform-backend
```

---

## 三、代码更新方法

### 方法一：Git拉取更新（推荐）

#### 1. 本地提交代码
```bash
# 在本地修改代码后
git add .
git commit -m "描述你的改动"
git push
```

#### 2. 服务器上更新
```bash
# 下载更新脚本（首次）
wget https://raw.githubusercontent.com/你的仓库/main/update.sh
chmod +x update.sh

# 运行更新
./update.sh
```

### 方法二：SCP上传文件

```bash
# 上传修改的文件
scp web/backend/main.py root@你的服务器IP:/opt/taskplatform/web/backend/
scp web/frontend/src/App.tsx root@你的服务器IP:/opt/taskplatform/web/frontend/src/

# 然后SSH登录服务器重启
ssh root@你的服务器IP
cd /opt/taskplatform/web/frontend && npm run build
sudo supervisorctl restart taskplatform-backend
```

### 方法三：GitHub Actions自动部署

创建 `.github/workflows/deploy.yml`：

```yaml
name: Deploy to Tencent Cloud

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/taskplatform
            git pull
            cd web/frontend && npm install && npm run build
            sudo supervisorctl restart taskplatform-backend
```

---

## 四、常用命令

### 查看服务状态
```bash
# 后端服务状态
sudo supervisorctl status taskplatform-backend

# Nginx状态
sudo systemctl status nginx

# 查看日志
tail -f /opt/taskplatform/logs/backend.log
```

### 重启服务
```bash
# 重启后端
sudo supervisorctl restart taskplatform-backend

# 重启Nginx
sudo systemctl reload nginx
```

### 端口检查
```bash
# 检查端口占用
netstat -tulpn | grep :80
netstat -tulpn | grep :8000
```

---

## 五、防火墙配置

### 腾讯云控制台设置

登录 [腾讯云控制台](https://console.cloud.tencent.com/)：

1. 进入「轻量应用服务器」→「防火墙」
2. 添加规则：
   - 端口：80 / 协议：TCP / 来源：0.0.0.0/0
   - 端口：443 / 协议：TCP / 来源：0.0.0.0/0

---

## 六、域名配置（可选）

### 1. 购买域名
- 腾讯云或其他域名服务商

### 2. DNS解析
- A记录 → 服务器IP

### 3. 配置SSL证书（免费）
```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 自动配置HTTPS
sudo certbot --nginx -d 你的域名.com
```

---

## 七、常见问题

### Q1: Nginx 502错误
```bash
# 检查后端是否运行
sudo supervisorctl status taskplatform-backend

# 重启后端
sudo supervisorctl restart taskplatform-backend
```

### Q2: 端口无法访问
- 检查腾讯云防火墙规则
- 检查服务器防火墙：`sudo ufw status`

### Q3: 依赖安装失败
```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 八、联系支持

如遇问题，请提供：
- 服务器IP
- 错误日志：`cat /opt/taskplatform/logs/backend.log`