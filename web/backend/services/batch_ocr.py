# -*- coding: utf-8 -*-
"""
批量OCR识别脚本 - 从价格截图提取数据
"""
import os
import re
import sqlite3
import logging
from datetime import datetime
from PIL import Image
import pytesseract

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tesseract路径
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 已知品牌映射（OCR识别错误的品牌名）
BRAND_MAPPING = {
    '西王': ['西王', 'BE', 'Aeen', 'Been', 'Been', 'Bcd', 'AB', 'RB'],
    '永锋': ['永锋', 'ET', 'ES', 'ES', 'Sueo0'],
    '莱钢': ['莱钢', 'KE', 'SSE', 'SFR'],
}

def get_brand_from_ocr(ocr_brand: str) -> str:
    """从OCR识别的品牌名映射到正确名称"""
    for brand, variants in BRAND_MAPPING.items():
        if ocr_brand in variants or ocr_brand.lower() == brand[:2].lower():
            return brand
    return ocr_brand

def parse_date_from_filename(filename: str) -> tuple:
    """从文件名解析日期和时间段"""
    # 文件名格式: screenshot_YYYYMMDD_AM.png 或 screenshot_YYYY-MM-DD_AM.png
    filename = os.path.basename(filename)

    # 提取日期部分
    date_match = re.search(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', filename)
    if date_match:
        date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
    else:
        return None, None

    # 提取时间段
    if '_PM' in filename or '_pm' in filename:
        period = 'PM'
        time_str = '15:00'
    else:
        period = 'AM'
        time_str = '09:00'

    return date, time_str

def ocr_image(image_path: str) -> list:
    """OCR识别图片中的价格数据"""
    try:
        img = Image.open(image_path)
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(img, lang='eng', config=custom_config)

        prices = []
        # 正则匹配: 规格 + 材质 + 品牌 + 价格
        pattern = r'([O0](?:6|8|10|12|14|16|18|20|22|25|28|32))\s+(HPB300|HRB400E|HRB500E)\s+(\w+)\s+(\d{3,4})'

        matches = re.findall(pattern, text)
        for m in matches:
            spec = m[0].replace('O', 'Ø').replace('0', 'Ø')
            material_type = m[1]
            # OCR识别的品牌可能有问题，尝试映射
            ocr_brand = m[2]
            # 简化处理：使用ocr识别的品牌，但做一些基础映射
            if ocr_brand.upper() in ['AB', 'BE', 'RB', 'KB', 'KE', 'ET', 'ES']:
                brand = get_brand_from_ocr(ocr_brand)
            else:
                brand = ocr_brand
            price = int(m[3])

            prices.append({
                'spec': spec,
                'material_type': material_type,
                'brand': brand,
                'price': price
            })

        return prices

    except Exception as e:
        logger.error(f"[ocr_image] 识别失败 {image_path}: {e}")
        return []

def process_screenshot(image_path: str, date: str, time_str: str) -> list:
    """处理单个截图，返回价格列表"""
    prices = ocr_image(image_path)

    result = []
    for p in prices:
        result.append({
            'date': date,
            'fetch_time': time_str,
            'material_name': '钢筋',  # 默认品名
            'spec': p['spec'],
            'material_type': p['material_type'],
            'brand': p['brand'],
            'price': p['price'],
            'price_change': None,
            'remark': 'OCR识别',
            'region': '山东烟台'
        })

    return result

def update_database(prices: list):
    """更新数据库"""
    if not prices:
        return 0

    conn = sqlite3.connect('web/backend/services/data/yantai_rebar.db')
    c = conn.cursor()

    inserted = 0
    for p in prices:
        try:
            c.execute('''
                INSERT INTO rebar_prices
                (date, fetch_time, material_name, spec, material_type, brand, price, price_change, remark, region)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                p['date'], p['fetch_time'], p['material_name'], p['spec'],
                p['material_type'], p['brand'], p['price'], p['price_change'],
                p['remark'], p['region']
            ))
            inserted += 1
        except Exception as e:
            logger.debug(f"插入跳过: {p['date']} - {p['spec']} - {e}")

    conn.commit()
    conn.close()

    return inserted

def main():
    """主函数"""
    logger.info("[batch_ocr] 开始批量OCR识别...")

    data_dir = 'web/backend/services/data'
    db_path = 'web/backend/services/data/yantai_rebar.db'

    # 获取数据库中已有的日期
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT DISTINCT date FROM rebar_prices')
    existing_dates = set(r[0] for r in c.fetchall())
    conn.close()

    # 找出所有截图
    screenshot_files = [
        f for f in os.listdir(data_dir)
        if f.startswith('screenshot_') and f.endswith('.png')
    ]

    logger.info(f"找到 {len(screenshot_files)} 个截图文件")

    total_inserted = 0
    processed_dates = set()
    errors = []

    for filename in sorted(screenshot_files):
        image_path = os.path.join(data_dir, filename)

        # 解析日期
        date, time_str = parse_date_from_filename(filename)
        if not date:
            logger.warning(f"无法解析日期: {filename}")
            continue

        # 跳过已有数据的日期
        if date in existing_dates and date not in processed_dates:
            logger.debug(f"跳过已有数据: {date}")
            continue

        logger.info(f"处理: {filename} -> {date} {time_str}")

        try:
            # OCR识别
            prices = process_screenshot(image_path, date, time_str)

            if prices:
                # 更新数据库
                inserted = update_database(prices)
                total_inserted += inserted
                processed_dates.add(date)
                logger.info(f"  插入 {inserted} 条记录")
            else:
                logger.warning(f"  未识别到价格数据")

        except Exception as e:
            logger.error(f"  处理失败: {e}")
            errors.append((filename, str(e)))

    logger.info(f"=== OCR处理完成 ===")
    logger.info(f"处理日期数: {len(processed_dates)}")
    logger.info(f"新增记录数: {total_inserted}")
    if errors:
        logger.warning(f"失败文件数: {len(errors)}")
        for f, e in errors[:5]:
            logger.warning(f"  {f}: {e}")

if __name__ == '__main__':
    main()