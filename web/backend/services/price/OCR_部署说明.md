# 钢筋价格截图识别 — OCR 部署说明

## 识别方案
- **主引擎**：RapidOCR（`rapidocr_onnxruntime`，基于 PP-OCR 模型，纯 onnxruntime，**不依赖大模型 / AI API**）
- **回退**：Tesseract（`pytesseract`，中文识别率低，仅 RapidOCR 不可用时兜底）
- 入口：`services/price/screenshot_recognizer.py` 的 `recognize_screenshot(image_path, hint_date, hint_period)`
- API：`POST /api/rebar/recognize-screenshot`（上传图片识别）→ 前端预览 → `POST /api/rebar/prices`（确认入库）

## 安装依赖

### 关键约束
`onnxruntime 1.16.x` + `numpy<2.0` 是已验证组合，三者必须一起 pin（详见 `requirements-ocr.txt`）：
- 新版 onnxruntime（1.20+）在部分 Windows 环境 DLL 初始化失败
- onnxruntime 1.16 是 numpy 1.x ABI 时代编译，配 numpy 2.x 会 `_ARRAY_API not found`

### 部署环境（腾讯云 / Linux）
    pip install -r web/backend/requirements-ocr.txt
（连同后端其他依赖 fastapi/uvicorn 等一起装到后端运行环境，recognizer 会直接 `import rapidocr`）

### 本机开发（隔离 venv，不污染全局）
    cd web/backend
    python -m venv .venv
    .venv/Scripts/python.exe -m pip install -r requirements-ocr.txt
    # 再装后端运行依赖到同一 venv，然后用 .venv 的 python 启动 uvicorn
后端用 `.venv` 的 python 启动后，`recognize_screenshot` 直接走 RapidOCR。

> 本机若用全局 python 跑后端且未装 rapidocr，会自动回退 Tesseract（识别率低）。

## 识别效果（以 mysteel 烟台价格长图实测）
| 字段 | 效果 |
|---|---|
| 材质（HPB300/HRB400E/HRB500E） | ✅ 准确（模糊匹配纠错 HFB→HPB、HRE→HRB） |
| 规格（Φ6/8/10/12/…/32） | ✅ 准确（补回 Φ 前缀） |
| 价格（元/吨） | ✅ 准确 |
| 品名（高线/螺纹钢） | ✅ 按材质推断 |
| 品牌/钢厂名 | ⚠️ 识别率低（小字中文），**前端预览让员工从下拉修正** |

一张长图约识别 60–70 条结构化记录，员工只需核对/补品牌名后确认入库。

## 不依赖大模型
本方案完全本地 OCR，员工 / 部署环境均无需配置 AI API。早期版本的「AI 视觉优先」路径已移除（因员工环境无大模型配置）。
