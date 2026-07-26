# -*- coding: utf-8 -*-
"""
截图识别服务 - 我的钢铁网（mysteel）山东烟台钢筋价格截图

策略：RapidOCR（本地，PP-OCR 模型）为主，Tesseract 回退。完全不依赖大模型/AI API，
适合无大模型配置的员工/部署环境。

识别流程：
1. （可选）PIL 放大 1.5x 提升小字识别率
2. RapidOCR 检测+识别所有文本框（含坐标）
3. 按 y 坐标聚类成行，行内按 x 排序
4. 对每段文本分类 + 领域纠错：
   - 价格：4 位数字（1500-6500）
   - 材质：模糊匹配到 HPB300/HRB400E/HRB500E（修正 HFB→HPB、HRE→HRB 等系统偏差）
   - 规格：数字 + Φ 前缀（修正 Φ 被识别为 4/0 的丢失）
   - 品牌：含中文或长字母的文本（识别率有限，留给前端预览人工修正）
5. 组装为入库记录（material_name 按材质推断）

本模块只识别不入库；入库由调用方（POST /api/rebar/prices）完成。
"""
import os
import re
import logging
import difflib
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

REGION = '山东烟台'
VALID_PERIODS = {'AM', 'PM'}
PERIOD_TO_TIME = {'AM': 'AM', 'PM': 'PM'}

# 放大倍数（提升小字识别率；None 表示不放大）
UPSCALE = 1.5
# 行聚类阈值（像素，y 方向）——同一行的文本框 cy 差值小于此值
ROW_TOL = 22

MATERIALS = ['HPB300', 'HRB400E', 'HRB500E']
VALID_SPECS = ['6', '6.5', '8', '10', '12', '14', '16', '18', '20', '22', '25', '28', '32']

# 从历史数据库统计的真实枚举（用于纠错 + 合理性校验，保证入库数据落在已知集合内）
BRANDS = ['石横特钢', '莱钢永锋', '江苏镔鑫', '莱钢', '日照', '永锋', '日钢营口', '敬业营口']
MATERIAL_NAMES = ['高线', '螺纹钢', '盘螺', '圆钢']
# 规格完整枚举（含范围规格，去 Φ 前缀比较）
VALID_SPECS_FULL = ['6', '6.5', '8', '10', '12', '14', '16', '18', '20', '22', '25', '28', '32', '36', '40',
                    '28-32', '12-14', '25-32', '12-22', '36-40']


# ============================================================
# 工具函数
# ============================================================
def _today_str() -> str:
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d')


def _valid_date(d: Optional[str]) -> Optional[str]:
    if not d:
        return None
    d = str(d).strip()
    return d if re.match(r'^\d{4}-\d{2}-\d{2}$', d) else None


def _valid_period(p: Optional[str]) -> Optional[str]:
    if not p:
        return None
    p = str(p).strip().upper()
    return p if p in VALID_PERIODS else None


def _guess_material_name(material_type: str) -> str:
    """根据材质推断品名"""
    mt = (material_type or '').upper()
    if 'HPB300' in mt:
        return '高线'
    if 'HRB' in mt:
        return '螺纹钢'
    return '钢筋'


def _fix_material(text: str) -> Optional[str]:
    """材质纠错：模糊匹配到 HPB300/HRB400E/HRB500E"""
    up = re.sub(r'[^A-Z0-9]', '', (text or '').upper())
    if not up or len(up) < 3:
        return None
    m = difflib.get_close_matches(up, MATERIALS, n=1, cutoff=0.55)
    return m[0] if m else None


def _fix_spec(text: str) -> Optional[str]:
    """规格纠错：提取数字 + Φ 前缀（修正 Φ 被识别为 4/0）"""
    digits = re.sub(r'[^0-9.]', '', text or '')
    if not digits:
        return None
    if digits in VALID_SPECS:
        return 'Φ' + digits
    # "410" / "010" -> Φ10（首位 4/0 是 Φ 的误识别）
    if len(digits) >= 2 and digits[0] in '40' and digits[1:] in VALID_SPECS:
        return 'Φ' + digits[1:]
    return None


def _is_brand_text(text: str) -> bool:
    """是否可能是品牌文本（含中文，或 2 字以上纯字母）"""
    if not text:
        return False
    if re.search(r'[一-鿿]', text):
        return True
    return bool(re.fullmatch(r'[A-Za-z]{2,}', text))


def _fix_brand(text: str) -> str:
    """
    品牌纠错：含中文则模糊匹配到已知钢厂名（BRANDS）；
    纯字母噪声（OCR 把中文钢厂名识别成 DELE 之类）无法匹配，原样返回留给前端人工修。
    """
    text = (text or '').strip()
    if not text:
        return ''
    if re.search(r'[一-鿿]', text):
        m = difflib.get_close_matches(text, BRANDS, n=1, cutoff=0.4)
        if m:
            return m[0]
    return text[:20]


def _spec_in_enum(spec: str) -> bool:
    """规格是否在已知枚举内（去 Φ 前缀比较）"""
    if not spec:
        return False
    s = spec.lstrip('Φ').strip()
    return s in VALID_SPECS_FULL


def _validate_record(rec: Dict[str, Any]) -> tuple:
    """
    合理性校验：检查价格区间、规格/品牌/品名是否落在已知枚举。
    返回 (valid: bool, issues: List[str])。issues 非空的行前端标红，员工必须核对。
    """
    issues = []
    if not rec.get('brand') or rec['brand'] not in BRANDS:
        issues.append('品牌待核对')
    if rec.get('spec') and not _spec_in_enum(rec['spec']):
        issues.append('规格异常')
    if not (1500 <= int(rec.get('price', 0)) <= 6500):
        issues.append('价格异常')
    if rec.get('material_name') not in MATERIAL_NAMES:
        issues.append('品名异常')
    return (len(issues) == 0), issues


# ============================================================
# RapidOCR（主引擎）
# ============================================================
_rapidocr_instance = None


def _get_rapidocr():
    """懒加载 RapidOCR 单例（首次调用加载模型，后续复用）"""
    global _rapidocr_instance
    if _rapidocr_instance is None:
        from rapidocr_onnxruntime import RapidOCR
        logger.info("[rapidocr] 初始化模型")
        _rapidocr_instance = RapidOCR()
    return _rapidocr_instance


def _rapidocr_available() -> bool:
    try:
        import rapidocr_onnxruntime  # noqa: F401
        return True
    except Exception:
        return False


def _upscale_image(image_path: str) -> str:
    """放大图片（返回新路径；失败返回原路径）"""
    if not UPSCALE:
        return image_path
    try:
        from PIL import Image
        img = Image.open(image_path)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        w, h = img.size
        big = img.resize((int(w * UPSCALE), int(h * UPSCALE)), Image.LANCZOS)
        big_path = os.path.splitext(image_path)[0] + '_big.png'
        big.save(big_path)
        logger.info(f"[rapidocr] 放大 {UPSCALE}x | {w}x{h} -> {big.size}")
        return big_path
    except Exception as e:
        logger.warning(f"[rapidocr] 放大失败，用原图 | {e}")
        return image_path


def _parse_records(raw_result) -> List[Dict[str, Any]]:
    """
    把 RapidOCR 原始结果解析为价格记录列表。

    Args:
        raw_result: RapidOCR 返回的 [[bbox, text, conf], ...] 或 None
    """
    if not raw_result:
        return []

    boxes = []
    for item in raw_result:
        try:
            box, text, conf = item[0], item[1], item[2]
            ys = [p[1] for p in box]
            xs = [p[0] for p in box]
            boxes.append({'cy': sum(ys) / 4, 'cx': sum(xs) / 4, 't': (text or '').strip()})
        except Exception:
            continue

    boxes.sort(key=lambda b: b['cy'])
    # 按 y 聚类成行
    rows: List[List[Dict]] = []
    cur: List[Dict] = []
    last_cy: Optional[float] = None
    for b in boxes:
        if last_cy is None or abs(b['cy'] - last_cy) <= ROW_TOL:
            cur.append(b)
        else:
            if cur:
                rows.append(cur)
            cur = [b]
        last_cy = b['cy']
    if cur:
        rows.append(cur)

    records: List[Dict[str, Any]] = []
    for row in rows:
        row.sort(key=lambda b: b['cx'])
        material = spec = price = None
        brand_parts: List[str] = []
        for b in row:
            t = b['t']
            if not t:
                continue
            if re.fullmatch(r'\d{4}', t):
                p = int(t)
                if 1500 <= p <= 6500:
                    price = p
                    continue
            m = _fix_material(t)
            if m:
                material = m
                continue
            s = _fix_spec(t)
            if s:
                spec = s
                continue
            if _is_brand_text(t):
                brand_parts.append(t)

        if price and (spec or material):
            brand = _fix_brand(''.join(brand_parts))
            rec = {
                'material_name': _guess_material_name(material or ''),
                'spec': spec or '',
                'material_type': material or '',
                'brand': brand,
                'price': price,
                'region': REGION,
            }
            rec['valid'], rec['issues'] = _validate_record(rec)
            records.append(rec)

    return records


def _recognize_by_rapidocr(image_path: str) -> Dict[str, Any]:
    """
    用 RapidOCR 识别。返回 {ok, prices, warnings}。
    优先直接 import（部署环境装了 rapidocr）；不可用时用 subprocess 调 venv python
    （本机开发：后端在全局 python 跑、rapidocr 装在 .venv）。
    """
    if _rapidocr_available():
        try:
            ocr = _get_rapidocr()
            target = _upscale_image(image_path)
            logger.info(f"[rapidocr] 开始识别(直接) | file={target}")
            result, elapse = ocr(target)
            if target != image_path:
                try:
                    os.remove(target)
                except Exception:
                    pass
            prices = _parse_records(result)
            logger.info(f"[rapidocr] 直接识别完成 | records={len(prices)}")
            if not prices:
                return {'ok': False, 'prices': [], 'warnings': ['RapidOCR 未解析出有效价格行']}
            return {'ok': True, 'prices': prices, 'warnings': []}
        except Exception as e:
            logger.warning(f"[rapidocr] 直接识别失败，改用 subprocess | {type(e).__name__}: {e}")

    return _recognize_via_subprocess(image_path)


def _recognize_via_subprocess(image_path: str) -> Dict[str, Any]:
    """通过 subprocess 调用 venv python 跑 rapidocr_runner.py（本机开发场景）。"""
    import subprocess
    import json
    from pathlib import Path

    backend_dir = Path(__file__).resolve().parent.parent.parent  # web/backend
    venv_py = backend_dir / '.venv' / 'Scripts' / 'python.exe'
    runner = backend_dir / 'services' / 'price' / 'rapidocr_runner.py'

    if not venv_py.exists():
        logger.warning(f"[rapidocr] venv python 不存在 | {venv_py}")
        return {'ok': False, 'prices': [],
                'warnings': ['未安装 rapidocr 且未找到 venv（请见 requirements-ocr.txt）']}

    logger.info(f"[rapidocr] subprocess 识别 | venv={venv_py}")
    try:
        proc = subprocess.run(
            [str(venv_py), str(runner), image_path],
            capture_output=True, text=True, timeout=300,
            encoding='utf-8', errors='replace',
        )
    except subprocess.TimeoutExpired:
        return {'ok': False, 'prices': [], 'warnings': ['RapidOCR 识别超时']}
    except Exception as e:
        return {'ok': False, 'prices': [], 'warnings': [f'subprocess 调用失败: {type(e).__name__}: {e}']}

    stdout = (proc.stdout or '').strip()
    try:
        data = json.loads(stdout)
    except Exception:
        logger.error(f"[rapidocr] runner 输出非 JSON | stderr={proc.stderr[-300:]}")
        return {'ok': False, 'prices': [], 'warnings': ['RapidOCR 输出解析失败']}

    if isinstance(data, dict) and 'error' in data:
        return {'ok': False, 'prices': [], 'warnings': [f'RapidOCR 错误: {data["error"]}']}

    prices = _parse_records(data)
    logger.info(f"[rapidocr] subprocess 识别完成 | records={len(prices)}")
    if not prices:
        return {'ok': False, 'prices': [], 'warnings': ['RapidOCR 未解析出有效价格行']}
    return {'ok': True, 'prices': prices, 'warnings': []}


# ============================================================
# Tesseract 回退
# ============================================================
def _recognize_by_tesseract(image_path: str) -> Dict[str, Any]:
    """Tesseract 回退识别（复用 ocr_missing）"""
    try:
        from services.ocr_missing import ocr_price_screenshot, normalize_brand
        raw = ocr_price_screenshot(image_path)
        prices: List[Dict[str, Any]] = []
        for p in raw:
            spec = (p.get('spec') or '').strip()
            mt = (p.get('material_type') or '').strip()
            brand = normalize_brand(p.get('brand', '')) or p.get('brand', '')
            try:
                price = int(p.get('price', 0))
            except (TypeError, ValueError):
                continue
            if price <= 0:
                continue
            rec = {
                'material_name': _guess_material_name(mt),
                'spec': spec,
                'material_type': mt,
                'brand': brand,
                'price': price,
                'region': REGION,
            }
            rec['valid'], rec['issues'] = _validate_record(rec)
            prices.append(rec)
        if not prices:
            return {'ok': False, 'prices': [], 'warnings': ['Tesseract 未识别到有效价格（可能未安装或图片不清晰）']}
        logger.info(f"[tesseract] 识别完成 | records={len(prices)}")
        return {'ok': True, 'prices': prices, 'warnings': []}
    except Exception as e:
        logger.error(f"[tesseract] 异常 | {type(e).__name__}: {e}", exc_info=True)
        return {'ok': False, 'prices': [], 'warnings': [f'Tesseract 异常: {type(e).__name__}: {e}']}


# ============================================================
# 对外入口
# ============================================================
async def recognize_screenshot(
    image_path: str,
    hint_date: Optional[str] = None,
    hint_period: Optional[str] = None,
) -> Dict[str, Any]:
    """
    识别我的钢铁网钢筋价格截图（RapidOCR 为主，Tesseract 回退）。仅识别，不入库。

    Args:
        image_path: 图片文件路径
        hint_date: 用户指定日期 YYYY-MM-DD（权威）
        hint_period: 用户指定时段 'AM' | 'PM'

    Returns:
        {success, method, date, period, fetch_time, prices, warnings}
    """
    hint_date = _valid_date(hint_date)
    hint_period = _valid_period(hint_period)
    logger.info(f"[recognize_screenshot] 开始 | file={image_path} | hint_date={hint_date} | hint_period={hint_period}")

    warnings: List[str] = []
    method: Optional[str] = None
    prices: List[Dict[str, Any]] = []

    # 1. RapidOCR 优先（_recognize_by_rapidocr 内部自动决定直接 import 还是 subprocess 调 venv）
    result = _recognize_by_rapidocr(image_path)
    if result['ok']:
        method = 'rapidocr'
        prices = result['prices']
    else:
        warnings.extend(result['warnings'])

    # 2. Tesseract 回退
    if not prices:
        if method:  # rapidocr 跑过但无结果
            logger.info("[recognize_screenshot] RapidOCR 无结果，回退 Tesseract")
        result = _recognize_by_tesseract(image_path)
        if result['ok']:
            method = method or 'tesseract'
            if not prices:
                method = 'tesseract'
            prices = result['prices']
        else:
            warnings.extend(result['warnings'])

    # 3. 日期 / 时段
    date = hint_date or _today_str()
    period = hint_period or 'AM'
    if period not in PERIOD_TO_TIME:
        period = 'AM'
    fetch_time = PERIOD_TO_TIME[period]

    if not hint_date:
        warnings.append(f'已使用日期 {date}，请确认入库前核对')

    success = bool(prices)
    logger.info(f"[recognize_screenshot] 完成 | success={success} | method={method} | count={len(prices)}")

    return {
        'success': success,
        'method': method,
        'date': date,
        'period': period,
        'fetch_time': fetch_time,
        'prices': prices,
        'warnings': warnings,
    }
