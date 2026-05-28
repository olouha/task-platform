# -*- coding: utf-8 -*-
"""
OCR价格识别脚本 - 使用表格结构提高识别准确率
"""
import os
import re
import sqlite3
import logging
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Tesseract路径
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 品牌OCR映射表
BRAND_MAP = {
    # 西王
    '西王': ['西王', 'Bcd', 'Aan', 'Aten', 'Bee', 'AB', 'BB', 'RB', 'RB', 'KB', 'Be'],
    # 永锋
    '永锋': ['永锋', 'KE', 'BE', 'SSE', 'ET', 'ES'],
    # 莱钢
    '莱钢': ['莱钢', 'LE', 'Lei', 'LEI', 'aL', 'Aen', 'Aee'],
    # 石横特钢
    '石横特钢': ['石横特钢', 'SHHT', 'SH', 'HH', 'HRB'],
    # 江苏镔鑫
    '江苏镔鑫': ['江苏镔鑫', 'BX', 'BXIN', '镔鑫'],
}

def create_brand_reverse_map():
    """创建反向映射表"""
    reverse_map = {}
    for brand, variants in BRAND_MAP.items():
        for v in variants:
            reverse_map[v.lower()] = brand
    return reverse_map

BRAND_REVERSE = create_brand_reverse_map()

def normalize_brand(ocr_text: str) -> str:
    """规范化品牌名称"""
    if not ocr_text:
        return ''

    ocr_lower = ocr_text.lower().strip()

    # 直接匹配
    if ocr_lower in BRAND_REVERSE:
        return BRAND_REVERSE[ocr_lower]

    # 模糊匹配
    for brand, variants in BRAND_MAP.items():
        for v in variants:
            if v.lower() in ocr_lower or ocr_lower in v.lower():
                return brand
            # 相似度匹配
            if len(v) > 2 and len(ocr_lower) > 2:
                if v[0].lower() == ocr_lower[0] and v[1].lower() == ocr_lower[1]:
                    return brand

    return ocr_text

def preprocess_image(image_path: str) -> Image.Image:
    """图像预处理"""
    img = Image.open(image_path)

    # 转换为灰度
    img = img.convert('L')

    # 增加对比度
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # 锐化
    img = img.filter(ImageFilter.SHARPEN)

    return img

def ocr_price_screenshot(image_path: str) -> list:
    """OCR识别价格截图"""
    try:
        # 预处理图像
        img = preprocess_image(image_path)

        # 使用表格识别模式
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(img, lang='eng', config=custom_config)

        prices = []

        # 匹配模式1: Ø6 HPB300 AB 3950
        pattern1 = r'([O0Ø](?:6|8|10|12|14|16|18|20|22|25|28|32))\s+(HPB300|HRB400E|HRB500E)\s+([A-Za-z]+)\s+(\d{3,4})'

        for match in re.finditer(pattern1, text):
            spec = match.group(1).replace('0', 'Ø').replace('O', 'Ø')
            material_type = match.group(2)
            ocr_brand = match.group(3)
            price = int(match.group(4))

            brand = normalize_brand(ocr_brand)

            prices.append({
                'spec': spec,
                'material_type': material_type,
                'brand': brand if brand else ocr_brand,
                'price': price
            })

        # 匹配模式2: 更宽松的匹配
        pattern2 = r'(?:Ø|O)(6|8|10|12|14|16|18|20|22|25|28|32)\s+(HPB|HRB[45]?00E?)\s+([A-Za-z]{2,6})\s+(\d{3,4})'

        for match in re.finditer(pattern2, text):
            spec = f'Ø{match.group(1)}'
            material_type = match.group(2)
            if not material_type.endswith('E'):
                material_type = material_type + 'E'
            ocr_brand = match.group(3)
            price = int(match.group(4))

            brand = normalize_brand(ocr_brand)

            # 去重
            exists = any(p['spec'] == spec and p['material_type'] == material_type and p['brand'] == brand for p in prices)
            if not exists:
                prices.append({
                    'spec': spec,
                    'material_type': material_type,
                    'brand': brand if brand else ocr_brand,
                    'price': price
                })

        return prices

    except Exception as e:
        logger.error(f"OCR识别失败: {e}")
        return []

def parse_date_from_filename(filename: str) -> tuple:
    """从文件名解析日期"""
    import re
    date_match = re.search(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', filename)
    if date_match:
        date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
    else:
        return None, None

    if '_PM' in filename:
        return date, '15:00'
    else:
        return date, '09:00'

def save_to_database(date: str, time_str: str, prices: list, remark: str = 'OCR识别') -> int:
    """保存到数据库"""
    if not prices:
        return 0

    conn = sqlite3.connect('web/backend/services/data/yantai_rebar.db')
    c = conn.cursor()

    inserted = 0
    for p in prices:
        try:
            c.execute('''
                INSERT OR IGNORE INTO rebar_prices
                (date, fetch_time, material_name, spec, material_type, brand, price, price_change, remark, region)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date, time_str, '钢筋', p['spec'], p['material_type'],
                p['brand'], p['price'], None, remark, '山东烟台'
            ))
            if c.rowcount > 0:
                inserted += 1
        except Exception as e:
            pass

    conn.commit()
    conn.close()
    return inserted

def get_missing_dates() -> set:
    """获取数据库中缺失的日期"""
    conn = sqlite3.connect('web/backend/services/data/yantai_rebar.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT date FROM rebar_prices')
    existing = set(r[0] for r in c.fetchall())
    conn.close()

    # 生成所有工作日
    from datetime import datetime, timedelta
    all_days = set()
    current = datetime(2024, 1, 1)
    end = datetime(2026, 5, 27)
    while current <= end:
        if current.weekday() < 5:
            all_days.add(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    return all_days - existing

def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始OCR识别缺失日期的价格数据")
    logger.info("=" * 50)

    data_dir = 'web/backend/services/data'
    missing_dates = get_missing_dates()

    logger.info(f"缺失日期数: {len(missing_dates)}")

    # 找出有截图的缺失日期
    screenshot_files = [f for f in os.listdir(data_dir) if f.startswith('screenshot_') and f.endswith('.png')]

    total_inserted = 0
    processed = 0

    for filename in sorted(screenshot_files):
        date, time_str = parse_date_from_filename(filename)

        if not date or date not in missing_dates:
            continue

        image_path = os.path.join(data_dir, filename)

        logger.info(f"处理: {date} ({time_str}) - {filename}")

        prices = ocr_price_screenshot(image_path)

        if prices:
            inserted = save_to_database(date, time_str, prices)
            total_inserted += inserted
            processed += 1
            logger.info(f"  识别: {len(prices)}条, 插入: {inserted}条")
        else:
            logger.info(f"  未识别到价格数据")

    logger.info("=" * 50)
    logger.info(f"OCR处理完成!")
    logger.info(f"处理日期: {processed}")
    logger.info(f"新增记录: {total_inserted}")
    logger.info("=" * 50)

if __name__ == '__main__':
    main()