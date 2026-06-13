# 临时解决方案：禁用 Supabase

## 方案说明
如果无法复制文件到服务器，可以通过修改配置文件禁用 Supabase，让系统直接使用 SQLite 数据库。

## 操作步骤

### 在服务器上操作：

1. **打开配置文件**
   - 路径：`C:\taskplatform\config\cloud.json`

2. **修改配置**
   将 Supabase URL 和 Key 设为空或注释掉：

   ```json
   {
     "mode": "sqlite",
     "supabase_url": "",
     "supabase_key": "",
     "version": "1.0.0"
   }
   ```

   或者删除这两行：
   ```json
   {
     "mode": "sqlite",
     "version": "1.0.0"
   }
   ```

3. **保存文件**

4. **重启后端服务**
   ```powershell
   cd C:\taskplatform
   taskkill /F /IM python.exe
   python -m uvicorn web.backend.main:app --host 0.0.0.0 --port 8000
   ```

5. **验证修复**
   - 访问：http://140.143.125.234/
   - 应该能看到价格数据

## 原理说明
- 禁用 Supabase 后，系统会直接使用 SQLite 数据库
- SQLite 数据库文件：`C:\taskplatform\web\backend\services\data\yantai_rebar.db`
- 包含 10764 条记录，415 个交易日的数据

## 恢复 Supabase（可选）
如果后续 Supabase 网络恢复，可以恢复配置：
```json
{
  "mode": "supabase",
  "supabase_url": "https://meegxgfiqbsfeeedpmui.supabase.co",
  "supabase_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "version": "1.0.0"
}
```

但建议同时应用代码修复（添加错误处理），以便 Supabase 不可用时自动回退。
