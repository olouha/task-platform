"""
分析 mysteeel 价格解密机制
"""
import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USERNAME = 'M6616592358'
PASSWORD = 'panhui199261'

async def analyze_decryption():
    """分析页面解密机制"""
    logger.info("启动浏览器...")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        locale='zh-CN'
    )

    # 注入反检测脚本
    await context.add_init_script('''
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    ''')

    page = await context.new_page()
    await page.goto('https://passport.mysteel.com/', wait_until='networkidle')

    # 登录
    logger.info("登录...")
    await page.fill('input[placeholder*="手机"]', USERNAME)
    await asyncio.sleep(1)

    inputs = await page.query_selector_all('input')
    for inp in inputs:
        inp_type = await inp.get_attribute('type')
        if inp_type == 'password':
            await inp.fill(PASSWORD)
            break

    await asyncio.sleep(1)
    await page.click('button:has-text("登录")')
    await asyncio.sleep(8)

    # 访问价格页面
    logger.info("访问价格页面...")
    await page.goto('https://jiancai.mysteel.com/m/24021210/placeholder.html',
                   wait_until='networkidle', timeout=60000)
    await asyncio.sleep(10)

    # 截图
    await page.screenshot(path='services/data/screenshots/analyze_page.png', full_page=True)

    # 分析加密元素
    logger.info("分析页面结构...")
    analysis = await page.evaluate('''
        () => {
            const result = {
                globalFunctions: [],
                encryptVars: [],
                priceElements: [],
                scripts: []
            };

            // 获取全局函数
            const funcPattern = /^(decrypt|decode|showPrice|getPrice|render|init|load)/;
            for (const key in window) {
                if (typeof window[key] === 'function' && funcPattern.test(key)) {
                    result.globalFunctions.push(key);
                }
            }

            // 查找加密元素
            const allElements = document.querySelectorAll('*');
            allElements.forEach(el => {
                const attrs = [];
                for (const attr of el.attributes) {
                    attrs.push({name: attr.name, value: attr.value});
                }
                if (attrs.some(a => a.name.includes('encrypt') || a.name.includes('price'))) {
                    result.priceElements.push({
                        tag: el.tagName,
                        attrs: attrs,
                        text: el.textContent?.trim()?.substring(0, 50)
                    });
                }
            });

            // 获取脚本内容
            const scripts = document.querySelectorAll('script');
            scripts.forEach((script, i) => {
                const src = script.src;
                const content = script.textContent?.substring(0, 500);
                if (src || content) {
                    result.scripts.push({
                        index: i,
                        src: src,
                        contentPreview: content?.substring(0, 200)
                    });
                }
            });

            // 查找加密相关属性
            const dataAttrs = document.querySelectorAll('[data-encrypt], [data-type="price"]');
            dataAttrs.forEach(el => {
                result.encryptVars.push({
                    tag: el.tagName,
                    class: el.className,
                    attrs: Object.fromEntries([...el.attributes].map(a => [a.name, a.value])),
                    text: el.textContent?.trim()?.substring(0, 100)
                });
            });

            return result;
        }
    ''')

    logger.info("\n=== 全局函数 ===")
    for func in analysis['globalFunctions']:
        logger.info(f"  - {func}")

    logger.info("\n=== 加密元素 ===")
    for el in analysis['priceElements'][:10]:
        logger.info(f"  {el['tag']}: attrs={el['attrs']}")

    logger.info("\n=== 数据属性元素 ===")
    for el in analysis['encryptVars'][:10]:
        logger.info(f"  {el['tag']}: class={el['class']}, text={el['text']}")

    logger.info("\n=== 脚本列表 ===")
    for s in analysis['scripts'][:10]:
        src = s['src'][:80] if s['src'] else 'inline'
        logger.info(f"  [{s['index']}] src={src}")

    # 保存完整分析
    import json
    with open('services/data/screenshots/decryption_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    logger.info("\n分析完成，已保存到 screenshots/decryption_analysis.json")

    # 尝试触发解密
    logger.info("\n尝试触发解密函数...")
    await page.evaluate('''
        () => {
            const funcs = ['decryptAll', 'decodePrice', 'showPrice', 'renderPrice', 'initPrice'];
            funcs.forEach(f => {
                if (typeof window[f] === 'function') {
                    console.log('Calling: ' + f);
                    window[f]();
                }
            });
        }
    ''')
    await asyncio.sleep(3)

    # 检查价格
    prices = await page.evaluate('''
        () => {
            const prices = [];
            const cells = document.querySelectorAll('td');
            cells.forEach(c => {
                const text = c.textContent.trim();
                if (/^\d{4}$/.test(text)) {
                    prices.push(text);
                }
            });
            return prices;
        }
    ''')
    logger.info(f"触发后价格: {prices[:10] if prices else '无价格'}")

    await asyncio.sleep(10)
    await browser.close()

if __name__ == '__main__':
    asyncio.run(analyze_decryption())
