"""
价格监控API修复 - Supabase回退逻辑错误处理
===============================================

修复文件：web/backend/api/yantai_db.py

问题：
- 服务器配置了 Supabase，但连接失败导致API返回500错误
- 价格监控页面显示无数据

修复内容：
- 为所有 Supabase 调用添加 try-except 错误处理
- Supabase 失败时自动回退到 SQLite
- 记录回退日志便于调试

部署步骤：
1. 将此文件复制到服务器 C:\taskplatform\web\backend\api\yantai_db.py
2. 重启后端服务（运行 C:\taskplatform\deploy\tencent_cloud\restart.ps1）
3. 访问 http://140.143.125.234/ 验证价格监控页面
4. 检查日志确认回退到 SQLite

修复端点：
- /api/yantai-rebar/stats
- /api/yantai-rebar/latest
- /api/yantai-rebar/range
- /api/yantai-rebar/trend
- /api/yantai-rebar/materials
- /api/yantai-rebar/specs
- /api/yantai-rebar/dates

数据统计：
- SQLite 数据库：C:\taskplatform\web\backend\services\data\yantai_rebar.db
- 总记录数：10764 条
- 日期数：415 天
- 日期范围：2024-01-02 ~ 2026-05-30
"""
