# -*- coding: utf-8 -*-
"""
llm.py —— 大模型调用封装模块

职责：
1. 从 .env 读取 OPENAI_API_KEY / OPENAI_BASE_URL / MODEL_NAME / CHAT_MODEL_NAME；
2. chat()：普通文本对话；
3. chat_with_image()：图文（多模态）对话，用于错题图片识别；
4. 未配置 API Key 时自动进入「演示模式」，返回内置模拟数据，保证程序开箱即跑。
"""

import base64
import io
import json
import os
import re

# 读取 .env 配置（若未安装 python-dotenv，也不影响演示模式运行）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # pragma: no cover
    pass

# ---------------- 环境变量 ----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
# 多模态模型（错题图片识别用）
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini").strip()
# 对话模型（聊天/画像/推荐用），未单独配置时复用 MODEL_NAME
CHAT_MODEL_NAME = os.getenv("CHAT_MODEL_NAME", MODEL_NAME).strip()

# 是否为演示模式：未配置 API Key => 不真实调用接口，返回模拟数据
DEMO_MODE = not OPENAI_API_KEY

# OpenAI 客户端（懒加载；演示模式下永远不会创建）
_client = None


def _get_client():
    """懒加载 OpenAI 客户端（兼容官方及各类 OpenAI 兼容接口）。"""
    global _client
    if _client is None:
        from openai import OpenAI  # 延迟导入：演示模式下即使未装 openai 也能运行
        _client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    return _client


# ============================ 普通文本对话 ============================
def chat(messages, temperature=0.7):
    """
    普通文本对话。

    参数:
        messages: list[dict]，如 [{"role": "user", "content": "你好"}]，
                  也可包含 {"role": "system", "content": ...} 作为系统提示。
        temperature: 生成随机性（0~2），越大越发散。
    返回:
        str: 模型回复文本。演示模式下返回模拟回复。
    """
    if DEMO_MODE:
        return _mock_chat_reply(messages)

    client = _get_client()
    resp = client.chat.completions.create(
        model=CHAT_MODEL_NAME,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content


# ============================ 图片对话（多模态） ============================
def chat_with_image(prompt, image_bytes, temperature=0.3):
    """
    发送「文字提示 + 图片」给多模态模型（用于错题拍照识别）。

    参数:
        prompt: str，提示词（一般来自 prompts.build_mistake_analysis_prompt）。
        image_bytes: bytes，图片原始字节（jpg/png 等）。
    返回:
        str: 模型回复文本。演示模式下返回内置的模拟分析 JSON。
    """
    if DEMO_MODE:
        return _mock_image_analysis()

    # 1. 先用 Pillow 压缩图片（最长边 1280），降低上传体积
    compressed = _compress_image(image_bytes, max_side=1280)
    # 2. 转 base64 并拼成 data URL
    b64 = base64.b64encode(compressed).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{b64}"

    client = _get_client()
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content


def _compress_image(image_bytes, max_side=1280):
    """用 Pillow 压缩图片：最长边缩放到 max_side，并转 JPEG 以减小体积。"""
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("未安装 Pillow，无法处理图片，请先执行: pip install Pillow")

    img = Image.open(io.BytesIO(image_bytes))
    # 带透明通道 / 调色板的图片先转 RGB，避免 JPEG 保存报错
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")
    # 等比缩放到最长边 max_side
    w, h = img.size
    if max(w, h) > max_side:
        scale = max_side / float(max(w, h))
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


# ============================================================================
#                        演示模式（内置模拟数据）
#   说明：以下代码仅在 DEMO_MODE=True 时生效，用于在无 API Key 的情况下
#   模拟真实大模型的返回效果，保证各页面完整可演示。
# ============================================================================

# 常见科目关键词，用于从文本中粗略识别科目
_SUBJECT_KEYWORDS = ["数学", "物理", "化学", "生物", "语文", "英语", "历史", "地理", "政治", "信息技术"]

# 模拟对话：AI 按轮次引导学生补全画像五要素（学段/目标/薄弱科目/偏好/每日时间）
_MOCK_CHAT_STEPS = [
    # 第 0 步：开场，先问学段
    "你好呀！我是你的专属学习伴侣 🎓（当前为演示模式，回复由内置模拟数据生成）\n\n"
    "为了帮你定制学习计划，我想先了解一下你：你现在处于什么学段呢？"
    "（比如高一、高二、高三、大一……）",
    # 第 1 步：问学习目标
    "收到！那你最近最重要的学习目标是什么呢？比如「高考提分」「打好基础」「四六级备考」或者「竞赛拓展」，都可以跟我说说～",
    # 第 2 步：问薄弱科目
    "明白了！那你觉得目前哪些科目或者知识点比较让你头疼？（比如「数学函数」「物理力学」……）",
    # 第 3 步：问学习偏好
    "了解～你平时更喜欢哪种学习方式呢？看视频讲解、刷题练习，还是读文章做总结？",
    # 第 4 步：问每日时间
    "好哒，最后一个问题：你每天大概能安排多少时间用来学习呢？（比如 30 分钟、1 小时）",
    # 第 5 步：收尾，引导生成画像
    "太好了，信息收集得差不多啦！✨\n\n点击下方的「✅ 根据对话生成画像」按钮，我就能为你建立专属学习画像；"
    "之后还可以去「📚 资源推荐」页面获取个性化资料哦～（演示模式下画像由关键词规则模拟提取）",
]


def _mock_chat_reply(messages):
    """演示模式：根据消息内容判断任务类型，返回对应的模拟回复。"""
    # 取最后一条用户消息
    last_user = ""
    user_turns = 0
    for m in messages:
        if isinstance(m, dict) and m.get("role") == "user":
            user_turns += 1
            last_user = str(m.get("content", ""))

    # 任务分流：画像提取 / 资源推荐 / 错题分析 / 学习伴侣闲聊
    if "提取学生画像" in last_user:
        return json.dumps(_mock_profile_from_text(last_user), ensure_ascii=False, indent=2)
    if "学习资源推荐" in last_user:
        return json.dumps(_mock_resources(last_user), ensure_ascii=False, indent=2)
    if "举一反三" in last_user or "错题" in last_user:
        # 文本方式的错题分析：复用内置模拟分析结果（与图片分析一致）
        return _mock_image_analysis()

    # 闲聊：按用户发言轮次返回预设的引导式回复
    if user_turns <= 0:
        return _MOCK_CHAT_STEPS[0]
    return _MOCK_CHAT_STEPS[min(user_turns, len(_MOCK_CHAT_STEPS) - 1)]


def _mock_image_analysis():
    """演示模式：返回一道二次函数错题的完整模拟分析（JSON 字符串）。"""
    return json.dumps(_MOCK_ANALYSIS, ensure_ascii=False, indent=2)


# 内置的模拟错题分析结果（题目、错因、解析、变式题一应俱全）
_MOCK_ANALYSIS = {
    "question": "已知函数 f(x) = x² - 2ax + 3 在区间 (-∞, 2] 上单调递减，求实数 a 的取值范围。",
    "subject": "数学",
    "knowledge_points": ["二次函数的对称轴", "函数的单调性", "区间与对称轴的位置关系"],
    "error_reason": (
        "把「函数在区间上单调递减」错误理解成了「函数值在区间内为负」，"
        "于是列出了 f(2) ≥ 0 之类的条件。实际上，二次函数的单调性由对称轴决定："
        "开口向上时，对称轴左侧递减、右侧递增，需要比较的是对称轴与区间端点的位置关系，"
        "而不是函数值的正负。"
    ),
    "correct_solution": (
        "**第一步：求对称轴。** 对 f(x) = x² - 2ax + 3，对称轴为 x = 2a / 2 = a，抛物线开口向上。\n\n"
        "**第二步：写出单调区间。** 开口向上的二次函数在 (-∞, a] 上单调递减，在 [a, +∞) 上单调递增。\n\n"
        "**第三步：比较区间。** 题目要求在 (-∞, 2] 上单调递减，即 (-∞, 2] 必须落在减区间 (-∞, a] 内，"
        "因此需满足 2 ≤ a，即 a ≥ 2。\n\n"
        "**第四步：验证。** 当 a = 2 时，f(x) = (x - 2)² - 1，在 (-∞, 2] 上确实单调递减，成立。\n\n"
        "**结论：** a 的取值范围是 [2, +∞)。\n\n"
        "**易错提醒：** 遇到「二次函数在给定区间上的单调性」问题，套路是——先求对称轴，"
        "再用「减区间 ⊆ (-∞, 对称轴]」或「增区间 ⊆ [对称轴, +∞)」列不等式。"
    ),
    "similar_questions": [
        {
            "question": "已知函数 f(x) = x² + (a - 1)x + 2 在区间 (-∞, 3] 上单调递减，求 a 的取值范围。",
            "answer": "a ≥ 3",
            "hint": "先求对称轴 x = (1 - a) / 2，再由「减区间在对称轴左侧」列不等式。",
        },
        {
            "question": "已知函数 f(x) = x² - 2ax + 1 在区间 (2, +∞) 上单调递增，求 a 的取值范围。",
            "answer": "a ≤ 2",
            "hint": "增区间在对称轴右侧，只需让区间起点 2 落在 [a, +∞) 内。",
        },
        {
            "question": "若函数 f(x) = x² + 2(a - 1)x + 3 在区间 (-∞, 4] 上单调递减，求 a 的取值范围。",
            "answer": "a ≤ -3",
            "hint": "注意这次对称轴是 x = 1 - a（一次项系数含 a），先化简再比较 4 与对称轴的位置。",
        },
        {
            "question": "（提升）已知函数 g(x) = x² - 2ax + 3 在区间 [a + 1, a + 2] 上的最小值为 0，求 a 的值。",
            "answer": "a = 2 或 a = -2",
            "hint": "对称轴 x = a 恒在区间左端点 a + 1 的左侧，所以最小值在左端点 x = a + 1 处取到，"
                    "令 g(a + 1) = -a² + 4 = 0 即可。",
        },
    ],
}


def _mock_profile_from_text(text):
    """
    演示模式：用关键词规则从对话文本中粗略提取学生画像，
    效果尽量接近真实大模型的输出。
    """
    text = text or ""

    # 若传入的是完整提示词，只截取「对话历史：」到「提取要求」之间的真实对话内容，
    # 避免提示词模板中的示例文字（如 "高一/高二/高三"）干扰关键词提取
    if "对话历史：" in text:
        text = text.split("对话历史：", 1)[1]
        if "提取要求" in text:
            text = text.split("提取要求", 1)[0]

    # 1. 学段：按优先级匹配
    grade = "高中在读"
    for g in ["高三", "高二", "高一", "初三", "初二", "初一", "大四", "大三", "大二", "大一"]:
        if g in text:
            grade = g
            break

    # 2. 科目：识别文本中出现的科目
    subjects = [s for s in _SUBJECT_KEYWORDS if s in text] or ["数学"]

    # 3. 薄弱科目：科目名附近（同一短句内，不跨逗号/分号）出现负面描述词
    weak = []
    neg_words = r"(薄弱|不好|较差|很差|差|头疼|困难|不行|丢分|不会|劣势|拖后腿)"
    gap = r"[^。！？\n，,、；;]"  # 匹配间隔时不允许跨越分句标点
    for s in subjects:
        if re.search(re.escape(s) + gap + r"{0,12}" + neg_words, text) or \
           re.search(neg_words + gap + r"{0,12}" + re.escape(s), text):
            weak.append(s)
    if not weak:
        weak = subjects[:1]

    # 4. 优势科目：出现的科目中排除薄弱项
    strengths = [s for s in subjects if s not in weak] or []

    # 5. 每日可用时间：优先匹配「每天/每日 xx 分钟」，其次匹配「xx 小时」
    daily = 60
    m = re.search(r"(?:每天|每日|一天)[^。！？\n]{0,6}?(\d+)\s*分钟", text) or \
        re.search(r"(\d+)\s*分钟", text)
    hm = re.search(r"(\d+(?:\.\d+)?)\s*小时", text)
    if m:
        daily = int(m.group(1))
    elif hm:
        daily = int(float(hm.group(1)) * 60)
    daily = max(10, min(daily, 600))

    # 6. 学习目标：按关键词归类
    if "高考" in text:
        goal = "稳步提升高考成绩"
    elif "竞赛" in text:
        goal = "拓展竞赛能力"
    elif "考研" in text:
        goal = "考研备考"
    elif "四六级" in text or "六级" in text:
        goal = "英语四六级备考"
    elif "基础" in text:
        goal = "夯实基础、查漏补缺"
    else:
        goal = "夯实基础、稳步提分"

    # 7. 学习偏好：按关键词识别
    prefs = []
    if "视频" in text:
        prefs.append("喜欢看视频讲解")
    if "刷题" in text or "做题" in text or "练习" in text:
        prefs.append("通过刷题巩固")
    if "文章" in text or "阅读" in text or "总结" in text:
        prefs.append("喜欢阅读与归纳总结")
    preferences = "、".join(prefs) if prefs else "讲解与练习结合"

    return {
        "grade": grade,
        "subjects": subjects,
        "goal": goal,
        "weak_points": weak,
        "strengths": strengths,
        "preferences": preferences,
        "daily_minutes": daily,
    }


def _mock_resources(prompt):
    """演示模式：根据提示词中嵌入的画像信息，生成模拟的资源推荐列表。"""
    # 从提示词文本里反查科目与薄弱点
    subjects = [s for s in _SUBJECT_KEYWORDS if s in prompt] or ["数学"]
    # 尝试读取每日可用时间
    m = re.search(r"每日可用学习时间：(\d+)\s*分钟", prompt)
    daily = int(m.group(1)) if m else 60
    main = subjects[0]

    items = [
        {
            "title": f"{main}核心考点思维导图（{len(subjects)}科通用版）",
            "type": "文章",
            "reason": f"一张图梳理{main}主干知识，快速定位薄弱点，适合每天花 10 分钟过一遍。",
            "keywords": [main, "知识梳理", "思维导图"],
        },
        {
            "title": f"{main}高频考点精讲视频合集",
            "type": "视频",
            "reason": "按专题拆解高频考点，先看 15 分钟视频再动笔，理解效率更高。",
            "keywords": [main, "视频课", "考点精讲"],
        },
        {
            "title": f"{main}分层变式题专项训练（基础 → 提高）",
            "type": "练习",
            "reason": "题目难度分三级，正好对应「错题 → 变式 → 综合」的进阶路径，建议每天 3-5 题。",
            "keywords": [main, "专项练习", "变式训练"],
        },
        {
            "title": "错题复盘方法指南：艾宾浩斯复习表怎么用",
            "type": "文章",
            "reason": "配合你的错题本使用：按 1 / 3 / 7 天周期回看错题，把「错过」变成「掌握」。",
            "keywords": ["学习方法", "错题复盘", "记忆曲线"],
        },
        {
            "title": f"{'、'.join(subjects[:3])} 学科规划示例：{daily} 分钟怎么分配",
            "type": "文章",
            "reason": f"结合你每天 {daily} 分钟的可支配时间，给出「视频 + 练习 + 复盘」的黄金配比方案。",
            "keywords": ["时间规划", "学习计划"] + subjects[:2],
        },
    ]
    return items
