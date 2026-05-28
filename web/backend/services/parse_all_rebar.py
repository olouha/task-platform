# -*- coding: utf-8 -*-
"""
OCR解析所有钢筋图片
"""
import os
import re
from paddleocr import PaddleOCR
from collections import defaultdict

BASE_DIR = r'C:\Users\admin\Desktop\近五年钢筋混凝土造价管理截图(1)\近五年钢筋混凝土造价管理截图'

ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)

def ocr_image(img_path):
    """OCR单张图片"""
    try:
        result = ocr.ocr(img_path, cls=True)
        if not result or not result[0]:
            return []
        items = []
        for line in result[0]:
            bbox, (text, conf) = line
            x1, y1 = bbox[0]
            x2, y2 = bbox[2]
            items.append({
                'x': (x1 + x2) / 2,
                'y': (y1 + y2) / 2,
                'text': text.strip(),
                'conf': conf
            })
        items.sort(key=lambda k: k['y'])
        return items
    except Exception as e:
        print(f"OCR错误 {img_path}: {e}")
        return []

def parse_rebar_image(img_path):
    """解析钢筋图片"""
    items = ocr_image(img_path)

    data = []
    rows = defaultdict(list)

    for item in items:
        y_group = round(item['y'] / 20) * 20
        rows[y_group].append(item)

    current_spec = None

    for y in sorted(rows.keys()):
        row_items = sorted(rows[y], key=lambda k: k['x'])
        row_text = ' '.join([item['text'] for item in row_items])

        # 检测钢筋规格
        grade_match = re.search(r'(HPB|HRB)\d*[E]?', row_text)
        size_match = re.search(r'[φ◎]?(\d+)', row_text)

        if grade_match and size_match:
            grade = grade_match.group(1)
            if 'E' in row_text or '抗震' in row_text:
                grade += 'E'
            size = size_match.group(1)

            # 找价格（同行X>300的数字）
            for item in row_items:
                if item['x'] > 300:
                    price_match = re.search(r'^(\d{3,4})', item['text'])
                    if price_match:
                        price = price_match.group(1)
                        data.append({
                            'grade': grade,
                            'size': size,
                            'price': int(price),
                            'spec': f"{grade}Φ{size}"
                        })
                        break

    return data

def main():
    all_data = defaultdict(lambda: defaultdict(list))

    # 遍历所有文件夹
    for year_folder in sorted(os.listdir(BASE_DIR)):
        year_path = os.path.join(BASE_DIR, year_folder)
        if not os.path.isdir(year_path):
            continue

        year_match = re.match(r'^(\d{4})年$', year_folder)
        if not year_match:
            continue
        year = year_match.group(1)

        for quarter_folder in sorted(os.listdir(year_path)):
            quarter_path = os.path.join(year_path, quarter_folder)
            if not os.path.isdir(quarter_path):
                continue

            # 标准化季度名
            q_match = re.search(r'第(.+?)季度', quarter_folder)
            if q_match:
                quarter_num = q_match.group(1)
                if year == '2021' or year == '2022' or year == '2023':
                    quarter = f"{quarter_num}"
                else:
                    quarter = f"{year}年{quarter_num}季度"
            else:
                quarter = quarter_folder

            # 找钢筋图片
            rebar_files = [f for f in os.listdir(quarter_path)
                          if f.startswith('钢筋') and f.endswith('.png')]

            if not rebar_files:
                continue

            print(f"\n处理 {year} {quarter}...")

            for rebar_file in rebar_files:
                rebar_path = os.path.join(quarter_path, rebar_file)
                data = parse_rebar_image(rebar_path)
                for item in data:
                    all_data[year][quarter].append(item)
                print(f"  {rebar_file}: {len(data)}条")

    # 输出结果
    print("\n\n=== 钢筋数据汇总 ===")
    for year in sorted(all_data.keys()):
        for quarter in sorted(all_data[year].keys()):
            data = all_data[year][quarter]
            if data:
                print(f"\n{year} {quarter}: {len(data)}条")
                for item in data[:5]:
                    print(f"  {item}")
                if len(data) > 5:
                    print(f"  ... 还有{len(data)-5}条")

    # 生成Python代码
    print("\n\n=== Python代码 ===")
    print("STEEL_REBAR_HISTORY = {")
    for year in sorted(all_data.keys()):
        quarters_with_data = {q: d for q, d in all_data[year].items() if d}
        if quarters_with_data:
            print(f'    "{year}": {{')
            for quarter in sorted(quarters_with_data.keys()):
                data = quarters_with_data[quarter]
                print(f'        "{quarter}": [')
                for item in data:
                    print(f'            {{"grade": "{item["grade"]}", "size": "{item["size"]}", "price": {item["price"]}, "spec": "{item["spec"]}"}},')
                print('        ],')
            print('    },')
    print("}")

if __name__ == '__main__':
    main()
