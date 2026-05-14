# TaskPlatform - 任务调度平台

模块化任务调度平台，支持功能扩展和打包分发。

## 功能特性

- **定时任务调度** - Cron表达式/间隔执行
- **网页数据抓取** - 自动抓取网页数据
- **浏览器自动化** - 自动登录/填写表单/点击
- **数据导出** - 支持 CSV/Excel/JSON
- **多数据库支持** - MySQL/PostgreSQL/SQLite
- **可视化界面** - PyQt6 桌面应用

## 项目结构

```
task-platform/
├── main.py              # 主入口
├── core/                # 核心模块
│   ├── scheduler.py     # 任务调度器
│   ├── database.py      # 数据库管理
│   └── db_config.py     # 数据库配置
├── ui/                  # 界面模块
│   ├── main_window.py   # 主窗口
│   └── tabs/            # 标签页
│       ├── dashboard_tab.py  # 仪表盘
│       ├── tasks_tab.py      # 任务管理
│       ├── scraper_tab.py     # 数据抓取
│       ├── export_tab.py      # 数据导出
│       ├── settings_tab.py    # 设置
│       └── logs_tab.py        # 日志
├── modules/             # 功能模块
│   ├── web_scraper.py       # 网页抓取
│   ├── browser_automation.py # 浏览器自动化
│   └── data_exporter.py     # 数据导出
├── config/              # 配置目录
├── exports/             # 导出文件目录
├── logs/                # 日志目录
├── requirements.txt     # 依赖
├── build.py             # 打包脚本
└── README.md
```

## 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- PyQt6 - 界面框架
- APScheduler - 任务调度
- requests - HTTP请求
- beautifulsoup4 - HTML解析
- openpyxl - Excel导出
- playwright/selenium - 浏览器自动化

## 使用方法

### 运行程序

```bash
python main.py
```

### 打包为 exe

```bash
pip install pyinstaller
python build.py
```

打包后 exe 位于 `dist/TaskPlatform.exe`

## 界面说明

1. **仪表盘** - 系统概览、统计信息
2. **任务管理** - 创建/编辑/删除普通任务
3. **数据抓取** - 配置网页抓取和浏览器自动化任务
4. **数据导出** - 导出任务数据到 CSV/Excel/JSON
5. **执行日志** - 查看任务执行记录
6. **设置** - 数据库配置、调度器设置

## 添加新功能

功能以模块形式添加在 `modules/` 目录：

```python
# modules/example_module.py
class ExampleTask:
    def __init__(self, task_data, database):
        self.task_data = task_data
        self.database = database

    def execute(self) -> bool:
        # 任务逻辑
        return True
```

然后在 `main.py` 中注册处理器：
```python
scheduler.register_handler('example', example_handler)
```

## 版本

v1.0.0 - 初始版本