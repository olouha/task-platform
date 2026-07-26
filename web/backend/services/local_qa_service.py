"""
本地知识库问答服务
不依赖外部AI，使用关键词匹配和模板回答
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


class LocalQAService:
    """本地问答服务 - 基于关键词匹配和规则"""

    def __init__(self):
        self.supabase = SupabaseService()

        # 意图分类规则
        self.intent_patterns = {
            "price_query": [
                r"价格|多少钱|查询|最新.*价|当前.*价",
                r"螺纹钢|钢筋|水泥|混凝土|砂石|材料"
            ],
            "price_trend": [
                r"趋势|涨跌|变化|走势|上涨|下跌",
                r"最近.*天|近.*周|近.*月"
            ],
            "adjustment_calc": [
                r"调差|调价|价差|计算",
                r"怎么算|如何算|公式"
            ],
            "material_info": [
                r"什么是|什么是|介绍|说明",
                r"钢筋|水泥|混凝土"
            ],
            "system_info": [
                r"系统|功能|怎么用|如何使用",
                r"帮助|help"
            ]
        }

        # 材料关键词映射
        self.material_keywords = {
            "螺纹钢": ["螺纹钢", "hrb400", "hrb400e", "螺纹"],
            "光圆钢筋": ["光圆", "hpb300", "圆钢"],
            "水泥": ["水泥", "p.o", "p.s"],
            "混凝土": ["混凝土", "砼", "c30", "c35", "c40"],
            "砂": ["砂", "砂子", "中砂", "细砂", "粗砂"],
            "石": ["石", "石子", "碎石", "石屑"],
            "砂浆": ["砂浆", "砌筑", "抹灰"]
        }

        # 日期解析模式
        self.date_patterns = {
            "today": r"今天|当日",
            "yesterday": r"昨天|昨日",
            "week": r"近.*周|最近一周|7天",
            "month": r"近.*月|最近一月|30天",
            "quarter": r"本季度|这季度",
            "year": r"今年|本年|近.*年",
            "year_specified": r"(\d{4})年",  # 新增：指定年份，如"2025年"
            "date": r"(\d{4})-(\d{1,2})-(\d{1,2})|(\d{4})年(\d{1,2})月(\d{1,2})日"
        }

    async def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict:
        """
        处理用户问答（主入口）

        参数:
            messages: 消息列表
            temperature: 温度参数（本地模式忽略）
            max_tokens: 最大token数（本地模式忽略）

        返回:
            AI响应格式
        """
        # 提取用户问题
        user_query = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_query = msg.get("content", "")
                break

        if not user_query:
            return self._error_response("未找到用户问题")

        logger.info(f"[LocalQA] 收到问题 | query={user_query[:50]}...")

        try:
            # 1. 识别意图
            intent = self._classify_intent(user_query)
            logger.info(f"[LocalQA] 意图识别 | intent={intent}")

            # 2. 提取参数
            params = self._extract_params(user_query, intent)
            logger.info(f"[LocalQA] 参数提取 | params={params}")

            # 3. 执行查询
            result = await self._execute_query(intent, params)
            logger.info(f"[LocalQA] 查询完成 | result_len={len(str(result))}")

            # 4. 生成回答
            answer = self._generate_answer(intent, result, params)
            logger.info(f"[LocalQA] 生成回答 | answer_len={len(answer)}")

            return self._format_response(answer)

        except Exception as e:
            logger.error(f"[LocalQA] 处理失败 | {e}", exc_info=True)
            return self._fallback_response(user_query)

    def _classify_intent(self, query: str) -> str:
        """
        识别用户意图

        返回: intent 类型
        """
        query_lower = query.lower()

        # 按优先级检查
        priority_order = ["price_trend", "price_query", "adjustment_calc", "material_info", "system_info"]

        for intent in priority_order:
            patterns = self.intent_patterns.get(intent, [])
            for pattern in patterns:
                if re.search(pattern, query):
                    return intent

        # 默认意图
        return "general"

    def _extract_params(self, query: str, intent: str) -> Dict:
        """
        提取查询参数

        返回: 参数字典
        """
        params = {
            "materials": [],
            "dates": {},
            "location": None,
            "spec": None
        }

        # 提取材料名称
        for material, keywords in self.material_keywords.items():
            for kw in keywords:
                if kw.lower() in query.lower():
                    if material not in params["materials"]:
                        params["materials"].append(material)

        # 提取日期
        if intent in ["price_query", "price_trend"]:
            params["dates"] = self._parse_dates(query)

        # 提取规格
        spec_match = re.search(r'(\d+)\s*(mm|毫米|Φ)?', query)
        if spec_match:
            params["spec"] = spec_match.group(1)

        return params

    def _parse_dates(self, query: str) -> Dict:
        """
        解析日期范围

        返回: {"start": date, "end": date}
        """
        today = datetime.now().date()
        dates = {}

        for key, pattern in self.date_patterns.items():
            if re.search(pattern, query):
                if key == "today":
                    dates = {"start": today, "end": today}
                elif key == "yesterday":
                    yesterday = today - timedelta(days=1)
                    dates = {"start": yesterday, "end": yesterday}
                elif key == "week":
                    start = today - timedelta(days=7)
                    dates = {"start": start, "end": today}
                elif key == "month":
                    start = today - timedelta(days=30)
                    dates = {"start": start, "end": today}
                elif key == "year":
                    start = today - timedelta(days=365)
                    dates = {"start": start, "end": today}
                elif key == "year_specified":
                    # 解析指定年份，如"2025年"
                    year_match = re.search(r'(\d{4})年', query)
                    if year_match:
                        try:
                            year = int(year_match.group(1))
                            # 该年份的1月1日到12月31日
                            start_date = datetime(year, 1, 1).date()
                            end_date = datetime(year, 12, 31).date()
                            dates = {"start": start_date, "end": end_date}
                        except:
                            pass
                elif key == "date":
                    # 尝试解析具体日期
                    date_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', query)
                    if date_match:
                        try:
                            date_obj = datetime(
                                int(date_match.group(1)),
                                int(date_match.group(2)),
                                int(date_match.group(3))
                            ).date()
                            dates = {"start": date_obj, "end": date_obj}
                        except:
                            pass
                break

        return dates

    async def _execute_query(self, intent: str, params: Dict) -> Dict:
        """
        执行数据库查询

        返回: 查询结果
        """
        if intent == "price_query":
            return await self._query_price(params)
        elif intent == "price_trend":
            return await self._query_price_trend(params)
        elif intent == "adjustment_calc":
            return await self._query_knowledge("调差计算")
        elif intent == "material_info":
            material = params["materials"][0] if params["materials"] else "材料"
            return await self._query_knowledge(material)
        elif intent == "system_info":
            return await self._query_knowledge("系统使用")
        else:
            # 通用查询：从知识库搜索
            return await self._search_knowledge(params)

    async def _query_price(self, params: Dict) -> Dict:
        """查询价格 - 使用本地 SQLite 数据库"""
        materials = params.get("materials", [])

        # 查询钢筋价格
        if any(m in ["螺纹钢", "光圆钢筋", "钢筋"] for m in materials):
            # 直接调用烟台价格API
            try:
                import sqlite3
                from pathlib import Path

                db_path = Path(__file__).parent.parent / "data" / "yantai_rebar.db"

                if not db_path.exists():
                    return {"type": "error", "data": [], "materials": materials}

                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                c = conn.cursor()

                # 查询最新日期的价格
                c.execute('SELECT MAX(date) FROM rebar_prices')
                max_date = c.fetchone()[0]

                if max_date:
                    c.execute(
                        'SELECT * FROM rebar_prices WHERE date = ? ORDER BY material_name, spec',
                        (max_date,)
                    )
                    rows = c.fetchall()
                    data = [dict(row) for row in rows]
                    conn.close()
                    return {"type": "rebar", "data": data, "materials": materials, "date": max_date}

                conn.close()
                return {"type": "rebar", "data": [], "materials": materials}

            except Exception as e:
                logger.error(f"[_query_price] SQLite查询失败 | {e}")
                return {"type": "error", "data": [], "materials": materials}

    async def _query_price_trend(self, params: Dict) -> Dict:
        """查询价格趋势 - 使用本地 SQLite 数据库"""
        materials = params.get("materials", [])
        dates = params.get("dates", {})

        # 钢筋趋势
        if any(m in ["螺纹钢", "光圆钢筋", "钢筋"] for m in materials):
            try:
                import sqlite3
                from pathlib import Path

                db_path = Path(__file__).parent.parent / "data" / "yantai_rebar.db"

                if not db_path.exists():
                    return {"type": "rebar_trend", "data": [], "materials": materials}

                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                c = conn.cursor()

                # 构建查询SQL
                if dates and dates.get("start") and dates.get("end"):
                    # 使用指定的日期范围
                    start_date = dates["start"].strftime("%Y-%m-%d")
                    end_date = dates["end"].strftime("%Y-%m-%d")
                    c.execute(f'''
                        SELECT date, AVG(price) as avg_price, MIN(price) as min_price, MAX(price) as max_price, COUNT(*) as cnt
                        FROM rebar_prices
                        WHERE date >= ? AND date <= ?
                        GROUP BY date
                        ORDER BY date ASC
                    ''', (start_date, end_date))
                else:
                    # 获取最近30天的数据
                    c.execute('''
                        SELECT date, AVG(price) as avg_price, MIN(price) as min_price, MAX(price) as max_price, COUNT(*) as cnt
                        FROM rebar_prices
                        WHERE date >= date('now', '-30 days')
                        GROUP BY date
                        ORDER BY date ASC
                    ''')
                rows = c.fetchall()
                trend = [dict(row) for row in rows]
                conn.close()

                return {"type": "rebar_trend", "success": True, "count": len(trend), "data": trend, "materials": materials}

            except Exception as e:
                logger.error(f"[_query_price_trend] SQLite查询失败 | {e}")
                return {"type": "rebar_trend", "data": [], "materials": materials}

        # 默认返回钢筋趋势
        return await self._query_price_trend({"materials": ["钢筋"]})

    async def _query_knowledge(self, topic: str) -> Dict:
        """从知识库查询主题内容"""
        docs = self.supabase.search_knowledge_base(query=topic, top_k=3)
        return {"type": "knowledge", "data": docs, "topic": topic}

    async def _search_knowledge(self, params: Dict) -> Dict:
        """通用知识库搜索"""
        materials = params.get("materials", [])
        query = " ".join(materials) if materials else "工程材料"

        docs = self.supabase.search_knowledge_base(query=query, top_k=3)
        return {"type": "knowledge", "data": docs, "query": query}

    def _generate_answer(self, intent: str, result: Dict, params: Dict) -> str:
        """
        生成自然语言回答

        返回: 回答文本
        """
        if intent == "price_query":
            return self._format_price_answer(result)
        elif intent == "price_trend":
            return self._format_trend_answer(result)
        elif intent == "adjustment_calc":
            return self._format_knowledge_answer(result, "调差计算")
        elif intent == "material_info":
            return self._format_material_info_answer(result, params)
        elif intent == "system_info":
            return self._format_system_info()
        else:
            return self._format_general_answer(result, params)

    def _format_price_answer(self, result: Dict) -> str:
        """格式化价格回答"""
        data = result.get("data", [])
        type_ = result.get("type")

        if not data:
            return "抱歉，暂无相关价格数据。请尝试查询其他材料或日期范围。"

        if type_ == "rebar":
            # 钢筋价格
            latest = data[0]
            answer = f"【钢筋价格查询】\n\n"
            answer += f"📅 查询日期：{latest.get('date', '未知')}\n"
            answer += f"📍 地区：{latest.get('region', '山东烟台')}\n\n"
            answer += f"💰 价格明细：\n"

            # 按材料分组
            materials: Dict[str, List[Dict]] = {}
            for item in data[:20]:  # 最多显示20条
                name = item.get('material_name', '未知')
                if name not in materials:
                    materials[name] = []
                materials[name].append(item)

            for name, items in materials.items():
                answer += f"\n🔩 {name}:\n"
                for item in items[:5]:  # 每个材料最多5条
                    spec = item.get('spec', '')
                    brand = item.get('brand', '')
                    price = item.get('price', 0)
                    answer += f"   - {spec} {brand}: ¥{price}/吨\n"

            answer += f"\n💡 数据来源：我的钢铁网"
            return answer

        else:
            # 造价参考价
            answer = f"【造价参考价格】\n\n"
            for item in data[:10]:
                name = item.get('name', '')
                unit_price = item.get('unit_price', 0)
                unit = item.get('unit', '')
                answer += f"📦 {name}: ¥{unit_price}/{unit}\n"

            return answer

    def _format_trend_answer(self, result: Dict) -> str:
        """格式化趋势回答"""
        # 直接获取 data，它已经是列表了
        data = result.get("data", [])

        if not data:
            return "暂无趋势数据。"

        answer = f"【价格趋势分析】\n\n"

        # 计算趋势
        if len(data) >= 2:
            first = data[0]
            last = data[-1]
            first_price = first.get("avg_price", 0)
            last_price = last.get("avg_price", 0)
            change = last_price - first_price
            change_pct = (change / first_price * 100) if first_price > 0 else 0

            answer += f"📈 趋势概览：\n"
            answer += f"   起始价格: ¥{first_price}/吨\n"
            answer += f"   最新价格: ¥{last_price}/吨\n"
            answer += f"   涨跌幅: {change:+.2f} ({change_pct:+.2f}%)\n\n"

            if change > 0:
                answer += "📊 总体呈上涨趋势\n"
            elif change < 0:
                answer += "📊 总体呈下跌趋势\n"
            else:
                answer += "📊 价格基本持平\n"

            answer += f"\n📅 数据点数: {len(data)} 个\n"
            answer += f"📅 时间范围: {last.get('date')} 至 {first.get('date')}\n"

        return answer

    def _format_knowledge_answer(self, result: Dict, topic: str) -> str:
        """格式化知识库回答"""
        docs = result.get("data", [])

        if not docs:
            return self._get_default_knowledge(topic)

        answer = f"【{topic}相关内容】\n\n"

        for i, doc in enumerate(docs[:3], 1):
            title = doc.get("title", "未命名")
            content = doc.get("content_chunk", doc.get("content", ""))[:300]
            answer += f"{i}. {title}\n"
            answer += f"   {content}...\n\n"

        return answer

    def _format_material_info_answer(self, result: Dict, params: Dict) -> str:
        """格式化材料信息回答"""
        materials = params.get("materials", [])
        if not materials:
            return "请提供要查询的材料名称，如：螺纹钢、水泥、混凝土等。"

        material = materials[0]
        docs = result.get("data", [])

        if docs:
            return self._format_knowledge_answer(result, material)

        # 使用内置材料信息
        return self._get_material_info(material)

    def _format_system_info(self) -> str:
        """格式化系统信息"""
        return """【工程材料管理系统 - 使用指南】

🔍 主要功能：

1. 价格查询
   - 查询最新材料价格
   - 查询历史价格数据
   - 支持按日期、材料类型筛选

2. 价格趋势
   - 查看价格涨跌趋势
   - 分析价格变化幅度
   - 支持多时间段对比

3. 调差计算
   - 项目材料调差计算
   - 支持多种调差方法
   - 自动生成计算报告

4. 数据管理
   - 项目信息管理
   - 材料库管理
   - 指标库管理

💡 使用示例：
- "查询螺纹钢价格"
- "最近一周钢筋价格趋势"
- "什么是调差计算？"
- "HRB400E Φ16 最新价格"

⚙️ 系统状态：本地问答模式
"""

    def _format_general_answer(self, result: Dict, params: Dict) -> str:
        """格式化通用回答"""
        docs = result.get("data", [])
        query = result.get("query", "")

        if docs:
            answer = f"为您找到以下相关信息：\n\n"
            for i, doc in enumerate(docs[:3], 1):
                title = doc.get("title", "未命名")
                content = doc.get("content_chunk", "")[:200]
                answer += f"{i}. {title}\n   {content}...\n\n"
            return answer

        return f"抱歉，我暂时无法理解您的问题「{query}」。\n\n您可以尝试：\n- 查询价格：\"XX材料价格\"\n- 查看趋势：\"最近一周价格趋势\"\n- 了解功能：\"系统帮助\""

    def _get_default_knowledge(self, topic: str) -> str:
        """获取默认知识库内容"""
        knowledge_base = {
            "调差计算": """【调差计算简介】

调差（价格调整）是指当工程材料价格波动超过合同约定幅度时，对合同价格进行调整的机制。

常见调差方法：
1. 简单比例法：按固定比例调整
2. 造价信息调整法：依据当地造价信息
3. 钢筋节点法：按节点价格计算

计算公式：
调差额 = Σ(材料用量 × 调差单价)
调差单价 = (本期价格 - 基准价格) × 调整系数
""",
            "系统使用": """【系统使用指南】

本系统提供以下功能：
- 价格查询：实时获取材料价格
- 趋势分析：查看价格变化趋势
- 调差计算：自动计算材料价差
- 数据管理：管理项目和材料数据

使用方式：直接输入问题即可，如：
- "查询螺纹钢价格"
- "最近一周价格趋势"
- "什么是调差计算？"
"""
        }

        return knowledge_base.get(topic, f"抱歉，暂无关于「{topic}」的知识库内容。")

    def _get_material_info(self, material: str) -> str:
        """获取材料信息"""
        material_info = {
            "螺纹钢": """【螺纹钢简介】

螺纹钢是建筑工程中常用的钢材，表面有螺旋形横肋。

常用规格：
- HRB400: 屈服强度400MPa
- HRB400E: 抗震钢筋
- HRB500: 高强度钢筋

常见直径：Φ12、Φ14、Φ16、Φ18、Φ20、Φ22、Φ25等

单位：吨
""",
            "水泥": """【水泥简介】

水泥是建筑工程最重要的胶凝材料。

常用品种：
- P.O 42.5: 普通硅酸盐水泥
- P.S 32.5: 矿渣硅酸盐水泥

用途：
- 混凝土配制
- 砂浆制作
- 地面找平

单位：吨
""",
            "混凝土": """【混凝土简介】

混凝土是由胶凝材料、骨料和水按一定比例配制而成。

常用强度等级：
- C30: 适用于一般建筑
- C35: 适用于高层建筑
- C40: 适用于重要结构

分类：
- 商品混凝土（泵送/非泵送）
- 现场搅拌混凝土

单位：立方米（m³）
"""
        }

        return material_info.get(material, f"抱歉，暂无「{material}」的详细资料。")

    def _format_response(self, content: str) -> Dict:
        """格式化为AI响应格式"""
        return {
            "id": "local-" + str(hash(content)),
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": "local-qa",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(content) // 2,
                "completion_tokens": len(content),
                "total_tokens": len(content) * 3 // 2
            }
        }

    def _error_response(self, message: str) -> Dict:
        """错误响应"""
        return self._format_response(f"❌ {message}")

    def _fallback_response(self, query: str) -> Dict:
        """回退响应"""
        return self._format_response(
            f"抱歉，处理您的问题时遇到错误。\n\n"
            f"您的问题：{query}\n\n"
            f"请尝试：\n"
            f"- 查询价格：\"XX材料价格\"\n"
            f"- 查看趋势：\"最近一周价格趋势\"\n"
            f"- 了解功能：\"系统帮助\""
        )


# 单例实例
local_qa_service = LocalQAService()
