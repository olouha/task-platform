# -*- coding: utf-8 -*-
"""
RapidOCR 命令行 runner —— 供 screenshot_recognizer 通过 subprocess 调用。

用途：当后端运行环境（全局 python）没装 rapidocr，而隔离 venv 装了时，
recognizer 用 venv 的 python 跑本脚本完成识别，避免污染后端运行环境。

输入：sys.argv[1] = 图片路径
输出：JSON 到 stdout，格式同 RapidOCR 原始 result：
    [[[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], text, conf], ...]
异常时输出 {"error": "..."}
"""
import sys
import os
import json

UPSCALE = 1.5


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': '缺少图片路径参数'}, ensure_ascii=False))
        return

    img_path = sys.argv[1]
    try:
        from PIL import Image
        from rapidocr_onnxruntime import RapidOCR

        img = Image.open(img_path)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        w, h = img.size

        # 放大提升小字识别率
        target = img_path
        if w > 0:
            big = img.resize((int(w * UPSCALE), int(h * UPSCALE)), Image.LANCZOS)
            target = os.path.splitext(img_path)[0] + '_big.png'
            big.save(target)

        ocr = RapidOCR()
        result, _ = ocr(target)

        if target != img_path:
            try:
                os.remove(target)
            except Exception:
                pass

        print(json.dumps(result if result else [], ensure_ascii=False))
    except Exception as e:
        print(json.dumps({'error': f'{type(e).__name__}: {e}'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
