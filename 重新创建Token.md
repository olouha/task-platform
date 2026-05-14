# 需要重新创建 Token

由于当前的 Token 权限不足，无法创建 KV 数据库。

## 请按以下步骤重新创建 Token：

1. 打开：https://dash.cloudflare.com/profile/api-tokens

2. 找到并点击你的 Token `TaskPlatform`

3. 点击 **"Edit"** 按钮

4. 或者直接 **删除这个 Token**，点击 **"Create Token"**

5. 选择 **"Create Custom Token"**

6. 点击 **"Start with a template"** 下拉菜单

7. 选择 **"Workers + Workers KV"**

8. 点击 **"Copy permissions"**

9. 设置：
   - Account permissions: Workers Scripts **(Edit)**
   - Zone permissions: 不需要
   - User permissions: 不需要

10. 点击 **"Continue to Summary"**

11. 点击 **"Create Token"**

12. **复制新的 Token**

---

把新 Token 发给我，我帮你完成部署！