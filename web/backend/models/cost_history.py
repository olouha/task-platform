# -*- coding: utf-8 -*-
from typing import List, Dict, Optional

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

# ============================================================
# 钢筋价格历史数据
# ============================================================

STEEL_REBAR_HISTORY: Dict[str, Dict[str, List[Dict]]] = {}


def get_available_periods():
    """获取所有可用时期"""
    periods = []
    for year in sorted(CONCRETE_HISTORY.keys()):
        for quarter in sorted(CONCRETE_HISTORY[year].keys()):
            # quarter 已经是完整格式如 "2021年一季度"
            periods.append({
                "year": year,
                "quarter": quarter,
                "label": quarter,
                "concrete_count": len(CONCRETE_HISTORY[year][quarter])
            })
    return sorted(periods, key=lambda x: (x["year"], x["quarter"]))


def get_concrete_prices(year: str, quarter: str) -> List[Dict]:
    """获取指定时期的混凝土价格"""
    if year in CONCRETE_HISTORY and quarter in CONCRETE_HISTORY[year]:
        return CONCRETE_HISTORY[year][quarter]
    return []


def get_steel_prices(year: str, quarter: str) -> List[Dict]:
    """获取指定时期的钢筋价格"""
    if year in STEEL_REBAR_HISTORY and quarter in STEEL_REBAR_HISTORY[year]:
        return STEEL_REBAR_HISTORY[year][quarter]
    return []
