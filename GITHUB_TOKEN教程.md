# GitHub 注册和 Token 创建教程

## 第一步：注册 GitHub 账号（3分钟）

1. 打开 https://github.com
2. 点击 "Sign up"（注册）
3. 输入邮箱地址
4. 设置密码
5. 设置用户名（随便起，比如 taskplatform2024）
6. 验证邮箱（去邮箱点击链接）
7. 完成！

---

## 第二步：创建 Personal Access Token（2分钟）

1. 登录后打开：https://github.com/settings/tokens
2. 点击 "Generate new token" → "Generate new token (classic)"
3. 设置：
   - Note（备注）: TaskPlatform
   - Expiration（过期时间）: 选择 "No expiration" 或 30 days
   - 勾选权限: `gist` （这个就够了）
4. 点击 "Generate token"
5. **重要：复制这个 token 保存好！**（只显示一次）

---

## 第三步：配置到程序

把 token 保存到项目目录：

1. 在 `e:/E/任务/task-platform/config/` 目录下
2. 创建一个文件叫 `github_token.txt`
3. 打开这个文件，粘贴你的 token
4. 保存

---

## 第四步：运行云端配置

在命令行运行：

```bash
cd e:/E/任务/task-platform
python 一键配置云端.py
```

如果 token 有效，就会自动创建共享 Gist！

---

## 常见问题

Q: Token 是什么？
A: Token 就是一把"钥匙"，让程序可以代表你操作 GitHub

Q: 安全吗？
A: 这个 token 只有创建 Gist 的权限，无法访问你的其他数据

Q: 忘记保存 token 怎么办？
A: 去 https://github.com/settings/tokens 删除旧的，重新创建一个