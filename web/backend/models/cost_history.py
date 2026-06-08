# -*- coding: utf-8 -*-
from typing import List, Dict, Optional
import sqlite3
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "services" / "data" / "cost_reference.db"

def _get_db_connection():
    """获取数据库连接"""
    return sqlite3.connect(DB_PATH)

# ============================================================
# 季度格式转换
# ============================================================

def _normalize_quarter(quarter: str) -> str:
    """将完整格式转为简化格式，用于数据库查询"""
    # 将 "2021年一季度" 转为 "一季度"
    for suffix in ['一季度', '二季度', '三季度', '四季度']:
        if suffix in quarter:
            return suffix
    return quarter


def _expand_quarter(year: str, quarter: str) -> str:
    """将简化格式转为完整格式，用于字典查询"""
    # 如果 quarter 已是完整格式，直接返回
    if '年' in quarter:
        return quarter
    # 将 "一季度" 转为 "2021年一季度"
    return f"{year}年{quarter}"


def _make_db_key(year: str, quarter: str) -> str:
    """将前端传来的 quarter 转换为数据库中存储的实际格式"""
    # 尝试查找匹配的 key
    if year in STEEL_REBAR_HISTORY:
        for key in STEEL_REBAR_HISTORY[year].keys():
            # 检查是否匹配
            if quarter in key or key in quarter:
                return key
    return quarter


def _get_steel_prices_from_db(year: str, quarter: str) -> List[Dict]:
    """从数据库获取指定时期的钢筋价格（支持两种格式）"""
    conn = _get_db_connection()
    c = conn.cursor()

    # 尝试多种查询方式
    queries = [
        (year, quarter),  # 完整格式如 "2022年二季度"
        (year, _normalize_quarter(quarter)),  # 简化格式如 "二季度"
    ]
    # 如果是简化格式也尝试完整格式
    if '年' not in quarter:
        for suffix in ['一季度', '二季度', '三季度', '四季度']:
            if suffix in quarter:
                queries.append((year, f"{year}年{quarter}"))
                break

    rows = []
    for q in queries:
        c.execute(
            'SELECT year, quarter, grade, spec, price FROM rebar_prices WHERE year = ? AND quarter = ?',
            list(q)
        )
        rows = c.fetchall()
        if rows:
            break

    conn.close()

    if not rows:
        return []

    result = []
    for row in rows:
        db_year, db_quarter, grade, spec, price = row
        result.append({
            "grade": grade,
            "size": spec,
            "price": price,
            "spec": f"Φ{spec}"
        })
    return result


# ============================================================
# 混凝土价格历史数据
# ============================================================

CONCRETE_HISTORY: Dict[str, Dict[str, List[Dict]]] = {
    "2021": {
        "2021年一季度": [
            {"grade": "C15", "yantai": 495, "rushan": 485},
            {"grade": "C20", "yantai": 505, "rushan": 495},
            {"grade": "C25", "yantai": 515, "rushan": 505},
            {"grade": "C30", "yantai": 525, "rushan": 515},
            {"grade": "C35", "yantai": 540, "rushan": 530},
            {"grade": "C40", "yantai": 560, "rushan": 550},
            {"grade": "C45", "yantai": 590, "rushan": 580},
            {"grade": "C50", "yantai": 630, "rushan": 620},
            {"grade": "C55", "yantai": 740, "rushan": 730},
        ],
        "2021年三季度": [
            {"grade": "C15", "yantai": 590, "rushan": 580},
            {"grade": "C20", "yantai": 600, "rushan": 590},
            {"grade": "C25", "yantai": 615, "rushan": 605},
            {"grade": "C30", "yantai": 630, "rushan": 620},
            {"grade": "C35", "yantai": 645, "rushan": 635},
            {"grade": "C40", "yantai": 665, "rushan": 655},
            {"grade": "C45", "yantai": 695, "rushan": 685},
            {"grade": "C50", "yantai": 735, "rushan": 725},
        ],
        "2021年二季度": [
            {"grade": "C15", "yantai": 580, "rushan": 570},
            {"grade": "C20", "yantai": 590, "rushan": 580},
            {"grade": "C25", "yantai": 600, "rushan": 590},
            {"grade": "C30", "yantai": 615, "rushan": 605},
            {"grade": "C35", "yantai": 630, "rushan": 620},
            {"grade": "C40", "yantai": 650, "rushan": 640},
            {"grade": "C45", "yantai": 680, "rushan": 670},
            {"grade": "C50", "yantai": 720, "rushan": 710},
        ],
        "2021年四季度": [
            {"grade": "C15", "yantai": 595, "rushan": 585},
            {"grade": "C20", "yantai": 605, "rushan": 595},
            {"grade": "C25", "yantai": 615, "rushan": 605},
            {"grade": "C30", "yantai": 625, "rushan": 615},
            {"grade": "C35", "yantai": 640, "rushan": 630},
            {"grade": "C40", "yantai": 660, "rushan": 650},
            {"grade": "C45", "yantai": 690, "rushan": 680},
            {"grade": "C50", "yantai": 730, "rushan": 720},
            {"grade": "C55", "yantai": 800, "rushan": 790},
            {"grade": "C60", "yantai": 840, "rushan": 830},
        ],
    },
    "2022": {
        "第一季度": [
            {"grade": "C15", "yantai": 595, "rushan": 585},
            {"grade": "C20", "yantai": 909, "rushan": 595},
            {"grade": "C25", "yantai": 615, "rushan": 605},
            {"grade": "C30", "yantai": 640, "rushan": 630},
            {"grade": "C40", "yantai": 660, "rushan": 650},
            {"grade": "C45", "yantai": 690, "rushan": 680},
            {"grade": "C50", "yantai": None, "rushan": 720},
            {"grade": "C55", "yantai": 800, "rushan": 790},
            {"grade": "C60", "yantai": 840, "rushan": 830},
        ],
        "第二季度": [
            {"grade": "C15", "yantai": 595, "rushan": 585},
            {"grade": "C20", "yantai": 605, "rushan": 595},
            {"grade": "C25", "yantai": 615, "rushan": 605},
            {"grade": "C30", "yantai": 625, "rushan": 615},
            {"grade": "C35", "yantai": 640, "rushan": 630},
            {"grade": "C40", "yantai": 660, "rushan": 650},
            {"grade": "C45", "yantai": 690, "rushan": 680},
            {"grade": "C50", "yantai": 730, "rushan": 720},
            {"grade": "C55", "yantai": 800, "rushan": 790},
            {"grade": "C60", "yantai": 840, "rushan": 830},
        ],
        "第三季度": [
            {"grade": "C15", "yantai": 566, "rushan": 556},
            {"grade": "C20", "yantai": 576, "rushan": 566},
            {"grade": "C25", "yantai": 586, "rushan": 576},
            {"grade": "C30", "yantai": 596, "rushan": 586},
            {"grade": "C35", "yantai": 611, "rushan": 601},
            {"grade": "C40", "yantai": 631, "rushan": 621},
            {"grade": "C45", "yantai": 661, "rushan": 651},
            {"grade": "C50", "yantai": 701, "rushan": 691},
            {"grade": "C55", "yantai": 771, "rushan": 761},
            {"grade": "C60", "yantai": 811, "rushan": 801},
        ],
        "第四季度": [
            {"grade": "C15", "yantai": 566, "rushan": None},
            {"grade": "C20", "yantai": 576, "rushan": None},
            {"grade": "C25", "yantai": 586, "rushan": None},
            {"grade": "C30", "yantai": 596, "rushan": None},
            {"grade": "C35", "yantai": 611, "rushan": 586},
            {"grade": "C40", "yantai": None, "rushan": 621},
            {"grade": "C45", "yantai": 661, "rushan": 651},
            {"grade": "C50", "yantai": 701, "rushan": 691},
            {"grade": "C55", "yantai": 811, "rushan": 801},
        ],
    },
    "2023": {
        "2023年一季度": [
            {"grade": "C20", "yantai": 581, "rushan": None},
            {"grade": "C30", "yantai": 591, "rushan": None},
            {"grade": "C40", "yantai": 606, "rushan": None},
            {"grade": "C45", "yantai": 656, "rushan": None},
            {"grade": "C50", "yantai": 696, "rushan": None},
            {"grade": "C55", "yantai": 766, "rushan": None},
            {"grade": "C60", "yantai": 806, "rushan": None},
        ],
        "2023年二季度": [
            {"grade": "C15", "yantai": 540, "rushan": None},
            {"grade": "C20", "yantai": 550, "rushan": 540},
            {"grade": "C25", "yantai": 560, "rushan": 550},
            {"grade": "C30", "yantai": 570, "rushan": 560},
            {"grade": "C40", "yantai": 585, "rushan": 570},
            {"grade": "C45", "yantai": 605, "rushan": 595},
            {"grade": "C50", "yantai": 635, "rushan": 625},
            {"grade": "C55", "yantai": 675, "rushan": 665},
            {"grade": "C60", "yantai": 745, "rushan": 735},
        ],
        "2023年三季度": [
            {"grade": "C15", "yantai": 450, "rushan": 440},
            {"grade": "C20", "yantai": 470, "rushan": 460},
            {"grade": "C30", "yantai": 480, "rushan": 470},
            {"grade": "C35", "yantai": 490, "rushan": 480},
            {"grade": "C40", "yantai": 500, "rushan": 490},
            {"grade": "C45", "yantai": 530, "rushan": 520},
            {"grade": "C50", "yantai": 560, "rushan": 550},
            {"grade": "C60", "yantai": 650, "rushan": 640},
        ],
        "2023年四季度": [
            {"grade": "C15", "yantai": 460, "rushan": 450},
            {"grade": "C25", "yantai": 470, "rushan": 460},
            {"grade": "C30", "yantai": 480, "rushan": 470},
            {"grade": "C35", "yantai": 490, "rushan": 490},
            {"grade": "C40", "yantai": 500, "rushan": 520},
            {"grade": "C45", "yantai": 530, "rushan": 550},
            {"grade": "C50", "yantai": 610, "rushan": 600},
            {"grade": "C55", "yantai": 650, "rushan": 640},
        ],
    },
    "2024": {
        "2024年一季度": [
            {"grade": "C15", "yantai": 450, "rushan": 440},
            {"grade": "C20", "yantai": 460, "rushan": 450},
            {"grade": "C25", "yantai": 480, "rushan": 470},
            {"grade": "C35", "yantai": 490, "rushan": 480},
            {"grade": "C40", "yantai": 500, "rushan": 490},
            {"grade": "C45", "yantai": 530, "rushan": 520},
            {"grade": "C50", "yantai": 560, "rushan": 550},
            {"grade": "C55", "yantai": 610, "rushan": 600},
            {"grade": "C60", "yantai": 650, "rushan": 640},
        ],
        "2024年二季度": [
            {"grade": "C15", "yantai": 450, "rushan": 440},
            {"grade": "C20", "yantai": 460, "rushan": 450},
            {"grade": "C25", "yantai": 470, "rushan": 460},
            {"grade": "C30", "yantai": 480, "rushan": 470},
            {"grade": "C35", "yantai": 490, "rushan": 480},
            {"grade": "C40", "yantai": 500, "rushan": 490},
            {"grade": "C45", "yantai": 530, "rushan": 520},
            {"grade": "C50", "yantai": 560, "rushan": 550},
            {"grade": "C55", "yantai": 610, "rushan": 600},
            {"grade": "C60", "yantai": 650, "rushan": 640},
        ],
        "2024年三季度": [
            {"grade": "C15", "yantai": 420, "rushan": None},
            {"grade": "C25", "yantai": 440, "rushan": None},
            {"grade": "C30", "yantai": 450, "rushan": None},
            {"grade": "C35", "yantai": 460, "rushan": None},
            {"grade": "C40", "yantai": 470, "rushan": None},
            {"grade": "C45", "yantai": 490, "rushan": None},
            {"grade": "C55", "yantai": 570, "rushan": None},
            {"grade": "C60", "yantai": 610, "rushan": None},
        ],
        "2024年四季度": [
            {"grade": "C15", "yantai": 460, "rushan": None},
            {"grade": "C20", "yantai": 470, "rushan": None},
            {"grade": "C25", "yantai": 480, "rushan": None},
            {"grade": "C30", "yantai": 490, "rushan": None},
            {"grade": "C35", "yantai": 510, "rushan": None},
            {"grade": "C45", "yantai": 530, "rushan": None},
            {"grade": "C50", "yantai": 560, "rushan": None},
            {"grade": "C55", "yantai": 650, "rushan": None},
        ],
    },
    "2025": {
        "2025年一季度": [
            {"grade": "C15", "yantai": 460, "rushan": None},
            {"grade": "C20", "yantai": 470, "rushan": None},
            {"grade": "C25", "yantai": 480, "rushan": None},
            {"grade": "C30", "yantai": 490, "rushan": None},
            {"grade": "C35", "yantai": 500, "rushan": None},
            {"grade": "C40", "yantai": 510, "rushan": None},
            {"grade": "C45", "yantai": 530, "rushan": None},
            {"grade": "C50", "yantai": 560, "rushan": None},
        ],
        "2025年二季度": [
            {"grade": "C15", "yantai": 450, "rushan": None},
            {"grade": "C20", "yantai": 460, "rushan": None},
            {"grade": "C25", "yantai": 470, "rushan": None},
            {"grade": "C30", "yantai": 480, "rushan": None},
            {"grade": "C35", "yantai": 490, "rushan": None},
            {"grade": "C40", "yantai": 500, "rushan": None},
            {"grade": "C45", "yantai": 520, "rushan": None},
            {"grade": "C50", "yantai": 550, "rushan": None},
        ],
        "2025年三季度": [
            {"grade": "C15", "yantai": 450, "rushan": None},
            {"grade": "C25", "yantai": 460, "rushan": None},
            {"grade": "C30", "yantai": 470, "rushan": None},
            {"grade": "C35", "yantai": 490, "rushan": None},
            {"grade": "C45", "yantai": 510, "rushan": None},
            {"grade": "C50", "yantai": 540, "rushan": None},
            {"grade": "C55", "yantai": 630, "rushan": None},
        ],
        "2025年四季度": [
            {"grade": "C20", "yantai": 460, "rushan": None},
            {"grade": "C25", "yantai": 480, "rushan": None},
            {"grade": "C30", "yantai": 490, "rushan": None},
            {"grade": "C40", "yantai": 500, "rushan": None},
            {"grade": "C45", "yantai": 550, "rushan": None},
            {"grade": "C50", "yantai": 600, "rushan": None},
            {"grade": "C60", "yantai": 640, "rushan": None},
        ],
    },
    "2026": {
        "2026年一季度": [
            {"grade": "C15", "yantai": 430, "rushan": None},
            {"grade": "C20", "yantai": 440, "rushan": None},
            {"grade": "C25", "yantai": 450, "rushan": None},
            {"grade": "C30", "yantai": 460, "rushan": None},
            {"grade": "C35", "yantai": 475, "rushan": None},
            {"grade": "C40", "yantai": 490, "rushan": None},
            {"grade": "C45", "yantai": 515, "rushan": None},
            {"grade": "C50", "yantai": 595, "rushan": None},
            {"grade": "C60", "yantai": 650, "rushan": None},
        ],
    },
}


def _expand_quarter_to_key(year: str, quarter: str) -> str:
    """将数据库中的 quarter 转换为完整的 key 格式"""
    # 如果已经是完整格式（包含年份），直接返回
    if f'{year}年' in quarter:
        return quarter
    # 将 "第一季度" 转为 "2022年二季度" 等
    return f"{year}年{quarter}"


def get_steel_rebar_history() -> Dict[str, Dict[str, List[Dict]]]:
    """从数据库加载钢筋历史数据"""
    if not DB_PATH.exists():
        return {}

    conn = _get_db_connection()
    c = conn.cursor()

    # 从数据库读取所有钢筋数据
    c.execute('SELECT year, quarter, grade, spec, price FROM rebar_prices ORDER BY year, quarter')
    rows = c.fetchall()
    conn.close()

    # 转换为字典格式，使用完整格式作为 key
    history = {}
    for row in rows:
        year, quarter, grade, spec, price = row
        if year not in history:
            history[year] = {}
        # 转换为完整格式 key
        key = _expand_quarter_to_key(year, quarter)
        if key not in history[year]:
            history[year][key] = []
        history[year][key].append({
            "grade": grade,
            "size": spec,
            "price": price,
            "spec": f"Φ{spec}"  # 添加规格显示格式
        })

    return history


# 延迟加载钢筋历史数据
STEEL_REBAR_HISTORY: Dict[str, Dict[str, List[Dict]]] = {}


def _load_steel_history():
    """加载钢筋历史数据到模块变量"""
    global STEEL_REBAR_HISTORY
    STEEL_REBAR_HISTORY = get_steel_rebar_history()


def get_available_periods():
    """获取所有可用时期"""
    periods = []
    for year in sorted(CONCRETE_HISTORY.keys()):
        for quarter in sorted(CONCRETE_HISTORY[year].keys()):
            # 统一转换为显示用的完整格式（中文数字）
            display_label = _convert_quarter_to_display_label(year, quarter)
            periods.append({
                "year": year,
                "quarter": quarter,  # 原始 key 用于查询
                "label": display_label,  # 显示用完整格式
                "concrete_count": len(CONCRETE_HISTORY[year][quarter])
            })
    return sorted(periods, key=lambda x: (x["year"], x["quarter"]))


def _convert_quarter_to_db_key(year: str, quarter: str) -> str:
    """将前端传来的完整格式转为数据库中的 key（简化格式）"""
    # 如果没有 '年'，说明已经是简化格式
    if '年' not in quarter:
        return quarter

    # 从完整格式提取简化格式
    # "2022年一季度" -> "第一季度"
    mapping = {
        '2022年一季度': '第一季度',
        '2022年二季度': '第二季度',
        '2022年三季度': '第三季度',
        '2022年四季度': '第四季度',
    }
    # 通用提取：去掉年份前缀
    for suffix in ['一季度', '二季度', '三季度', '四季度']:
        if suffix in quarter:
            return f'第{suffix}'
    return quarter


def _convert_quarter_to_display_label(year: str, quarter: str) -> str:
    """将简化格式转为显示用的完整格式（中文数字）"""
    if '年' in quarter:
        return quarter  # 已经是完整格式
    # "第一季度" -> "2022年一季度"
    mapping = {
        '第一季度': '一季度',
        '第二季度': '二季度',
        '第三季度': '三季度',
        '第四季度': '四季度',
    }
    suffix = mapping.get(quarter, quarter)
    return f"{year}年{suffix}"


def get_concrete_prices(year: str, quarter: str) -> List[Dict]:
    """获取指定时期的混凝土价格"""
    if year in CONCRETE_HISTORY:
        # 首先尝试直接匹配
        if quarter in CONCRETE_HISTORY[year]:
            return CONCRETE_HISTORY[year][quarter]

        # 尝试转换为数据库 key（简化格式）
        db_key = _convert_quarter_to_db_key(year, quarter)
        if db_key in CONCRETE_HISTORY[year]:
            return CONCRETE_HISTORY[year][db_key]
    return []


def get_steel_prices(year: str, quarter: str) -> List[Dict]:
    """获取指定时期的钢筋价格（从数据库）"""
    # 首先尝试从预加载数据中获取
    if year in STEEL_REBAR_HISTORY:
        if quarter in STEEL_REBAR_HISTORY[year]:
            return STEEL_REBAR_HISTORY[year][quarter]

        # 尝试简化格式匹配
        simplified = _normalize_quarter(quarter)
        if simplified != quarter:
            for key in STEEL_REBAR_HISTORY[year].keys():
                if simplified in key or key == f"{year}年{simplified}":
                    return STEEL_REBAR_HISTORY[year][key]

        # 尝试在 key 中模糊匹配
        for key in STEEL_REBAR_HISTORY[year].keys():
            if quarter in key or key in quarter:
                return STEEL_REBAR_HISTORY[year][key]

    # 如果预加载数据中没有，直接从数据库查询
    return _get_steel_prices_from_db(year, quarter)


# 启动时加载钢筋历史数据
try:
    _load_steel_history()
except Exception:
    pass  # 数据库可能不存在，忽略错误
