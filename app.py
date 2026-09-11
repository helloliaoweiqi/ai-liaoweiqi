#-*-coding: utf-8-*-
import os
import re
import json
import uuid

import streamlit as st
form utils import llm,prompts,storage

st.write("ok")

st.set_page_config(
    page_title="智学伴侣‑AI个性化学习助手",
    page_icon="📚",
    layout="wide"
)

PAGES = ["🏠 首页", "📸 AI错题本", "👤 学习画像", "📚 资源推荐"]
SUBJECTS = ["数学", "物理", "化学", "生物", "语文", "英语", "历史", "地理", "政治", "信息技术"]

# 画像对话的 AI 开场白
_GREETING = (
    "你好呀！我是你的专属学习伴侣 🎓 很高兴认识你！\n\n"
    "为了帮你定制更合适的学习计划，我想先了解一些你的情况：\n"
    "1️⃣ 你现在处于什么学段？（高一 / 高二 / 高三 / 大一……）\n"
    "2️⃣ 最近最重要的学习目标是什么？\n"
    "3️⃣ 有哪些科目或知识点让你比较头疼？\n"
    "4️⃣ 你更喜欢哪种学习方式？\n"
    "5️⃣ 每天大概能安排多少时间学习？\n\n"
    "不用一次答完，随便聊，想到什么说什么就行～"
)

# ---------------- 简洁现代风格的自定义样式 ----------------
st.markdown(
    """
    <style>
    /* 隐藏 Streamlit 默认菜单与页脚 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* 顶部渐变欢迎卡片 */
    .hero {background: linear-gradient(135deg, #5B7CFA, #8A63F5);
           border-radius: 18px; padding: 2.2rem 2.5rem; margin-bottom: 1.4rem;}
    .hero h1 {color: #ffffff; margin: 0; font-size: 1.85rem; font-weight: 700;}
    .hero p {color: #EAE6FF; margin: .5rem 0 0 0; font-size: 1rem;}
    /* 标签胶囊 */
    .chip {display: inline-block; padding: .12rem .7rem; border-radius: 999px;
           font-size: .8rem; margin: 0 .3rem .3rem 0; line-height: 1.5;}
    .chip-blue   {background: #E8F0FE; color: #1A56DB;}
    .chip-green  {background: #E6F6EC; color: #0F7B3E;}
    .chip-orange {background: #FEF3E2; color: #B25E09;}
    .chip-purple {background: #F1EAFE; color: #6D28D9;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================================
#                              通用小工具
# ============================================================================
def chip(text, color="blue"):
    """生成一个 HTML 小标签胶囊。"""
    return f'<span class="chip chip-{color}">{text}</span>'


def go_to(page_name):
    """生成页面跳转回调：点击按钮后切换侧边栏导航到指定页面。"""
    def _callback():
        st.session_state["nav_page"] = page_name
    return _callback


def extract_json(text):
    """
    从大模型返回的文本中提取 JSON（兼容 ```json 代码块、前后夹杂说明文字等情况）。

    返回:
        解析成功返回 dict / list；失败返回 None。
    """
    if not text:
        return None
    text = text.strip()

    # 1. 优先提取 Markdown 代码块内容
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()

    # 2. 直接尝试解析
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # 3. 截取第一个 { ... } 或 [ ... ] 再试
    for start_ch, end_ch in (("{", "}"), ("[", "]")):
        s, e = text.find(start_ch), text.rfind(end_ch)
        if s != -1 and e > s:
            try:
                return json.loads(text[s:e + 1])
            except (json.JSONDecodeError, ValueError):
                continue
    return None


def parse_profile_completion(profile):
    """计算画像完成度（0~100 的整数）。"""
    fields = [
        profile.get("grade"), profile.get("goal"), profile.get("subjects"),
        profile.get("weak_points"), profile.get("strengths"),
        profile.get("preferences"), profile.get("daily_minutes"),
    ]
    filled = sum(1 for f in fields if f)
    return int(filled / len(fields) * 100)


def render_analysis(data):
    """渲染一次错题分析结果：题目、知识点、错因、解析、变式题。"""
    st.divider()
    st.markdown(f"### 📝 题目")
    st.markdown(data.get("question", "（未识别到题目）"))
    kps = data.get("knowledge_points", []) or []
    if kps:
        st.markdown("🧩 知识点：" + "".join(chip(k, "purple") for k in kps), unsafe_allow_html=True)

    st.markdown("### ⚠️ 错误原因")
    st.info(data.get("error_reason", "暂无"))

    st.markdown("### ✅ 详细解析")
    st.markdown(data.get("correct_solution", "暂无"))

    sims = data.get("similar_questions", []) or []
    st.markdown(f"### 🎯 举一反三（{len(sims)} 道变式题）")
    for i, q in enumerate(sims, 1):
        with st.expander(f"变式题 {i}：{str(q.get('question', ''))[:48]}"):
            st.markdown(q.get("question", ""))
            st.markdown(f"**💡 提示：** {q.get('hint', '——')}")
            st.markdown(f"**🔑 参考答案：** {q.get('answer', '——')}")


# ============================================================================
#                              🏠 首页
# ============================================================================
def show_home():
    profile = storage.load_profile()
    mistakes = storage.load_mistakes()
    conversation = storage.load_conversation()
    completion = parse_profile_completion(profile)

    # 欢迎横幅
    st.markdown(
        """
        <div class="hero">
            <h1>🎓 智学伴侣 · 让每一次错题都成为进步的台阶</h1>
            <p>AI 错题分析 · 举一反三 · 对话式学习画像 · 个性化资源推荐</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 学习统计
    c1, c2, c3 = st.columns(3)
    c1.metric("📖 错题总数", f"{len(mistakes)} 道")
    c2.metric("👤 画像完成度", f"{completion}%")
    user_rounds = sum(1 for m in conversation if m.get("role") == "user")
    c3.metric("💬 画像对话轮数", f"{user_rounds} 轮")

    # 快捷入口
    st.subheader("🚀 快捷入口")
    b1, b2, b3 = st.columns(3)
    b1.button("📸 上传错题，AI 举一反三", on_click=go_to("📸 AI错题本"), use_container_width=True)
    b2.button("🗣️ 对话构建我的学习画像", on_click=go_to("👤 学习画像"), use_container_width=True)
    b3.button("📚 获取个性化资源推荐", on_click=go_to("📚 资源推荐"), use_container_width=True)

    # 最近错题预览
    if mistakes:
        st.subheader("🕒 最近添加的错题")
        for m in reversed(mistakes[-3:]):
            st.markdown(
                f"- **【{m.get('subject', '未知')}】** {str(m.get('question', ''))[:40]}"
                f"…（{m.get('created_at', '')}）"
            )
    else:
        st.info("错题本还是空的～点击上方「📸 上传错题」，体验 AI 分析 + 变式题生成吧！")


# ============================================================================
#                            📸 AI 错题本
# ============================================================================
def show_mistake_book():
    st.subheader("📸 AI 错题本")
    st.caption("拍照上传错题 → AI 分析错因并详细解析 → 自动生成 3-5 道同类变式题")
    if llm.DEMO_MODE:
        st.info("🧪 当前为**演示模式**：AI 分析结果为内置模拟数据；在 `.env` 中配置 API Key 后即可真实调用。")

    tab_upload, tab_book = st.tabs(["📤 上传错题", "📖 我的错题本"])

    # ---------------- Tab 1：上传错题 ----------------
    with tab_upload:
        col_img, col_text = st.columns(2)
        with col_img:
            uploaded = st.file_uploader("上传错题图片（支持 jpg / png）", type=["jpg", "jpeg", "png"])
            if uploaded is not None:
                st.image(uploaded, caption="题目图片预览", use_container_width=True)
        with col_text:
            manual_text = st.text_area(
                "或手动输入题目文本（可选，作为备选）",
                height=120,
                placeholder="例如：已知函数 f(x)=x²-2ax+3 在区间 (-∞,2] 上单调递减，求 a 的取值范围…",
            )
            subject = st.selectbox("选择科目", SUBJECTS, index=0)

        analyze_clicked = st.button("🔍 AI 分析并生成变式题", type="primary", use_container_width=True)

        if analyze_clicked:
            if uploaded is None and not manual_text.strip():
                st.warning("请先上传题目图片，或输入题目文本～")
            else:
                profile = storage.load_profile()
                base_prompt = prompts.build_mistake_analysis_prompt(profile, subject=subject)
                with st.spinner("AI 正在分析错题并生成变式题，请稍候…"):
                    try:
                        if uploaded is not None:
                            # 优先使用图片走多模态识别
                            raw = llm.chat_with_image(base_prompt, uploaded.getvalue())
                        else:
                            # 备选：直接把题目文本交给对话模型
                            raw = llm.chat([
                                {"role": "user", "content": base_prompt + "\n\n题目文本：\n" + manual_text.strip()}
                            ])
                    except Exception as e:  # 网络异常 / 接口报错等
                        st.error(f"AI 调用失败：{e}")
                        raw = None

                if raw:
                    data = extract_json(raw)
                    if not data:
                        st.error("AI 返回的内容解析失败，请重试一次。")
                        with st.expander("查看 AI 原始返回"):
                            st.code(str(raw))
                    else:
                        # 结果存入 session_state，保证后续操作（如保存）时页面不丢
                        st.session_state["last_analysis"] = data
                        st.session_state["last_analysis_subject"] = subject
                        st.session_state["last_analysis_image"] = uploaded.getvalue() if uploaded is not None else None

        # 展示最近一次分析结果（刷新/保存后依然可见）
        if st.session_state.get("last_analysis"):
            render_analysis(st.session_state["last_analysis"])
            if st.button("💾 保存到错题本", type="secondary", use_container_width=True):
                analysis = st.session_state["last_analysis"]
                mid = uuid.uuid4().hex[:12]
                img_path = None
                img_bytes = st.session_state.get("last_analysis_image")
                if img_bytes:
                    img_path = storage.save_mistake_image(img_bytes, mid)
                storage.add_mistake({
                    "id": mid,
                    "subject": analysis.get("subject") or st.session_state.get("last_analysis_subject", "未分类"),
                    "question": analysis.get("question", ""),
                    "knowledge_points": analysis.get("knowledge_points", []),
                    "error_reason": analysis.get("error_reason", ""),
                    "correct_solution": analysis.get("correct_solution", ""),
                    "similar_questions": analysis.get("similar_questions", []),
                    "source": "图片上传" if img_bytes else "文本输入",
                    "image_path": img_path,
                })
                # 清空暂存，避免重复保存
                for key in ("last_analysis", "last_analysis_subject", "last_analysis_image"):
                    st.session_state.pop(key, None)
                st.success("✅ 已保存到错题本！切到「📖 我的错题本」即可查看。")

    # ---------------- Tab 2：我的错题本 ----------------
    with tab_book:
        mistakes = storage.load_mistakes()
        if not mistakes:
            st.info("错题本还是空的～先去「📤 上传错题」体验 AI 分析吧！")
        else:
            # 按科目筛选
            subject_options = ["全部"] + sorted({m.get("subject", "未知") for m in mistakes})
            sel = st.selectbox("按科目筛选", subject_options)
            shown = [m for m in mistakes if sel == "全部" or m.get("subject") == sel]
            shown = list(reversed(shown))  # 最新添加的排前面
            st.caption(f"共 {len(shown)} 道错题")

            for m in shown:
                title = str(m.get("question", ""))[:38] or "（无题目文本）"
                with st.expander(f"【{m.get('subject', '未知')}】{title}…（{m.get('created_at', '')}）"):
                    # 原题图片（若有）
                    img_path = m.get("image_path")
                    if img_path and os.path.exists(img_path):
                        st.image(img_path, caption="原题图片", width=320)
                    kps = m.get("knowledge_points", []) or []
                    if kps:
                        st.markdown("🧩 知识点：" + "".join(chip(k, "purple") for k in kps), unsafe_allow_html=True)
                    st.markdown("**⚠️ 错误原因**")
                    st.info(m.get("error_reason", "暂无"))
                    st.markdown("**✅ 详细解析**")
                    st.markdown(m.get("correct_solution", "暂无"))
                    for i, q in enumerate(m.get("similar_questions", []) or [], 1):
                        with st.expander(f"变式题 {i}：{str(q.get('question', ''))[:36]}"):
                            st.markdown(q.get("question", ""))
                            st.markdown(f"**💡 提示：** {q.get('hint', '——')}")
                            st.markdown(f"**🔑 参考答案：** {q.get('answer', '——')}")
                    if st.button("🗑️ 删除这道错题", key=f"del_{m.get('id')}"):
                        storage.delete_mistake(m.get("id"))
                        st.rerun()


# ============================================================================
#                             👤 学习画像
# ============================================================================
def show_profile():
    st.subheader("👤 学习画像")
    profile = storage.load_profile()

    # 操作成功提示（配合 rerun 显示一次）
    if st.session_state.get("profile_saved_msg"):
        st.success(st.session_state.pop("profile_saved_msg"))

    # ---------------- 顶部：当前画像概览 ----------------
    if profile.get("completed"):
        st.markdown("#### 当前画像")
        c1, c2, c3 = st.columns(3)
        c1.metric("🎓 学段", profile.get("grade") or "—")
        c2.metric("🎯 学习目标", profile.get("goal") or "—")
        c3.metric("⏰ 每日可用时间", f"{profile.get('daily_minutes', 0)} 分钟")
        r1, r2 = st.columns(2)
        r1.markdown(
            "📘 学习科目：" + ("".join(chip(s, "blue") for s in profile.get("subjects", [])) or "—"),
            unsafe_allow_html=True,
        )
        r1.markdown(
            "⚠️ 薄弱科目：" + ("".join(chip(s, "orange") for s in profile.get("weak_points", [])) or "—"),
            unsafe_allow_html=True,
        )
        r2.markdown(
            "💪 优势：" + ("".join(chip(s, "green") for s in profile.get("strengths", [])) or "—"),
            unsafe_allow_html=True,
        )
        r2.markdown(f"💡 学习偏好：{profile.get('preferences') or '—'}")
    else:
        st.info("还没有学习画像～可以通过下方「🗣️ 对话式构建」或「✍️ 手动编辑」创建，"
                "画像越完整，AI 分析和推荐就越精准！")

    # ---------------- 手动编辑表单（备选方式） ---------------
    with st.expander("✍️ 手动编辑画像（备选方式）"):
        with st.form("manual_profile_form"):
            f_grade = st.text_input("学段", value=profile.get("grade", ""), placeholder="如：高二 / 大一")

            raw_subjects = profile.get("subjects", [])
            safe_subjects = [s for s in raw_subjects if s in SUBJECTS]
            f_subjects = st.multiselect("学习科目", SUBJECTS, default=safe_subjects)

            f_goal = st.text_input("学习目标", value=profile.get("goal", ""), placeholder="如：高考数学 130+")

            raw_weak = profile.get("weak_points", [])
            safe_weak = [s for s in raw_weak if s in SUBJECTS]
            f_weak = st.multiselect("薄弱科目 / 知识点", SUBJECTS, default=safe_weak)

            raw_strong = profile.get("strengths", [])
            safe_strong = [s for s in raw_strong if s in SUBJECTS]
            f_strong = st.multiselect("优势科目／知识点", SUBJECTS, default=safe_strong)

            f_pref = st.text_input(
                "学习偏好",
                value=profile.get("preferences", ""),
                placeholder="如：喜欢看视频讲解 + 适量刷题",
            )
            f_minutes = st.number_input(
                "每日可用学习时间（分钟）",
                min_value=10,
                max_value=600,
                value=int(profile.get("daily_minutes") or 60),
                step=10,
            )
            submitted = st.form_submit_button("💾 保存画像", type="primary")

            if submitted:
                storage.save_profile({
                    **profile,
                    "grade": f_grade.strip(),
                    "subjects": f_subjects,
                    "goal": f_goal.strip(),
                    "weak_points": f_weak,
                    "strengths": f_strong,
                    "preferences": f_pref.strip(),
                    "daily_minutes": int(f_minutes),
                    "completed": True,
                })
                st.session_state["profile_saved_msg"] = "✅ 画像已保存！可前往「📚 资源推荐」获取个性化资料～"
                st.rerun()

    # ---------------- 对话式构建画像 ----------------
    st.divider()
    head_col, clear_col = st.columns([4, 1])
    head_col.markdown("#### 🗣️ 对话式构建画像")
    if clear_col.button("🧹 清空对话", use_container_width=True):
        storage.save_conversation([])
        st.session_state.pop("profile_saved_msg", None)
        st.rerun()

    conv = storage.load_conversation()
    if not conv:
        # 首次进入：AI 先打招呼并抛出引导问题
        conv = [{"role": "assistant", "content": _GREETING}]
        storage.save_conversation(conv)

    # 渲染历史对话
    for msg in conv:
        with st.chat_message("user" if msg.get("role") == "user" else "assistant"):
            st.markdown(msg.get("content", ""))

    # 用户输入
    user_input = st.chat_input("例如：我是一名高二学生，数学函数部分比较薄弱，每天能学 1 小时…")
    if user_input:
        conv.append({"role": "user", "content": user_input})
        storage.save_conversation(conv)

        system_prompt = prompts.build_chat_system_prompt(profile)
        messages = [{"role": "system", "content": system_prompt}] + conv
        with st.spinner("AI 正在思考…"):
            try:
                reply = llm.chat(messages)
            except Exception as e:
                st.error(f"AI 调用失败：{e}")
                reply = ""
        if reply:
            conv.append({"role": "assistant", "content": reply})
            storage.save_conversation(conv)
        st.rerun()

    # ---------------- 生成 / 更新画像按钮 ----------------
    st.markdown("#### 🧩 生成 / 更新画像")
    st.caption("聊得差不多了？点击按钮，AI 会从对话中提炼出你的专属学习画像。")
    if st.button("✅ 根据对话生成画像", type="primary"):
        if not any(m.get("role") == "user" for m in conv):
            st.warning("请先和 AI 聊几句你的学习情况～")
        else:
            prompt = prompts.build_profile_prompt(conv)
            with st.spinner("正在提炼你的学习画像…"):
                try:
                    raw = llm.chat([{"role": "user", "content": prompt}])
                except Exception as e:
                    st.error(f"AI 调用失败：{e}")
                    raw = None
            data = extract_json(raw) if raw else None
            if isinstance(data, dict):
                storage.save_profile({**profile, **data, "completed": True})
                st.session_state["profile_saved_msg"] = "🎉 学习画像已生成！可前往「📚 资源推荐」获取个性化资料～"
                st.rerun()
            else:
                st.error("画像解析失败，请重试，或使用上方「手动编辑画像」表单。")


# ============================================================================
#                             📚 资源推荐
# ============================================================================
def show_resources():
    st.subheader("📚 资源推荐")
    st.caption("根据你的学习画像，AI 为你挑选真正有用的学习资源")
    profile = storage.load_profile()

    # 画像不完整时拦截
    if not profile.get("completed"):
        st.warning("你还没有完善的学习画像，AI 暂时无法为你推荐资源～")
        st.button("👉 去「👤 学习画像」页面完善画像", on_click=go_to("👤 学习画像"), type="primary")
        return

    # 画像摘要
    weak = profile.get("weak_points", []) or []
    st.markdown(
        "根据你的画像：" + ("".join(chip(w, "orange") for w in weak) or "（暂无薄弱点记录）")
        + "　🎯 " + (profile.get("goal") or "——"),
        unsafe_allow_html=True,
    )

    has_res = bool(st.session_state.get("resources"))
    btn_label = "🔄 重新生成推荐" if has_res else "✨ 生成个性化推荐"
    if st.button(btn_label, type="primary"):
        prompt = prompts.build_resource_prompt(profile)
        with st.spinner("AI 正在为你挑选学习资源…"):
            try:
                raw = llm.chat([{"role": "user", "content": prompt}])
            except Exception as e:
                st.error(f"AI 调用失败：{e}")
                raw = None
        data = extract_json(raw) if raw else None
        if not data:
            st.error("推荐结果解析失败，请点击重新生成再试一次。")
        else:
            st.session_state["resources"] = data
            has_res = True

    # 展示推荐结果
    resources = st.session_state.get("resources")
    if resources:
        st.markdown(f"### 为你推荐 {len(resources)} 个资源")
        for r in resources:
            with st.container(border=True):
                st.markdown(f"**📄 {r.get('title', '未命名资源')}**")
                type_chip = chip(f"{r.get('type', '资源')}", "purple")
                keywords = "".join(chip(k, "green") for k in (r.get("keywords", []) or []))
                st.markdown(type_chip + keywords, unsafe_allow_html=True)
                st.markdown(f"💡 {r.get('reason', '')}")
    else:
        st.info("点击上方按钮，获取为你量身定制的学习资源～")


# ============================================================================
#                              主入口
# ============================================================================
def main():
    with st.sidebar:
        st.markdown("## 🎓 智学伴侣")
        st.caption("AI 个性化学习助手 · 本地运行")
        st.divider()
        page = st.radio("功能导航", PAGES, key="nav_page", label_visibility="collapsed")
        st.divider()
        if llm.DEMO_MODE:
            st.info(
                "🧪 **演示模式**\n\n"
                "未检测到 API Key，所有 AI 回复均为内置模拟数据。\n\n"
                "在项目根目录 `.env` 中配置 `OPENAI_API_KEY` 等变量后重启，即可启用真实 AI。"
            )
        else:
            st.success(f"🤖 已连接模型\n\n`{llm.CHAT_MODEL_NAME}`")
        st.divider()
        st.caption("💾 数据保存在本地 data/ 目录，不上传任何隐私信息。")

    if page == "🏠 首页":
        show_home()
    elif page == "📸 AI错题本":
        show_mistake_book()
    elif page == "👤 学习画像":
        show_profile()
    else:
        show_resources()


if __name__ == "__main__":
    main()
