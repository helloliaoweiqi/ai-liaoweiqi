# -*- coding: utf-8 -*-
"""
storage.py —— 本地 JSON 数据存储模块

所有数据以 JSON 文件形式保存在项目根目录的 data/ 下，无需数据库：
- data/profile.json       学生画像
- data/mistakes.json      错题本（列表）
- data/conversation.json  画像对话历史（列表）
- data/images/            错题原图（可选）
"""

import json
import os
import uuid
from datetime import datetime

# 项目根目录（本文件位于 utils/ 下，上一级即项目根）
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_BASE_DIR, "data")
PROFILE_FILE = os.path.join(DATA_DIR, "profile.json")
MISTAKES_FILE = os.path.join(DATA_DIR, "mistakes.json")
CONVERSATION_FILE = os.path.join(DATA_DIR, "conversation.json")
IMAGE_DIR = os.path.join(DATA_DIR, "images")

# 默认学生画像结构（completed 表示画像是否已经生成过）
_DEFAULT_PROFILE = {
    "grade": "",
    "subjects": [],
    "goal": "",
    "weak_points": [],
    "strengths": [],
    "preferences": "",
    "daily_minutes": 60,
    "completed": False,
}


def _ensure_data_dir():
    """确保 data/ 目录存在（自动生成，无需手动创建）。"""
    os.makedirs(DATA_DIR, exist_ok=True)


def _read_json(path, default):
    """读取 JSON 文件；文件不存在或内容损坏时返回默认值。"""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return default


def _write_json(path, data):
    """写入 JSON 文件（UTF-8 编码、ensure_ascii=False 保留中文、缩进美化）。"""
    _ensure_data_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================ 学生画像 ============================
def load_profile():
    """读取学生画像；不存在时返回默认空画像。"""
    data = _read_json(PROFILE_FILE, {})
    return {**_DEFAULT_PROFILE, **data} if isinstance(data, dict) else dict(_DEFAULT_PROFILE)


def save_profile(profile):
    """保存学生画像（整体覆盖写入）。"""
    _write_json(PROFILE_FILE, profile)


# ============================ 错题本 ============================
def load_mistakes():
    """读取所有错题；不存在时返回空列表。"""
    data = _read_json(MISTAKES_FILE, [])
    return data if isinstance(data, list) else []


def add_mistake(mistake):
    """
    新增一道错题，自动补充 id 与创建时间，返回带 id 的完整记录。

    参数:
        mistake: dict，错题内容（question / subject / error_reason /
                 correct_solution / similar_questions 等字段）。
    """
    mistakes = load_mistakes()
    record = {
        **mistake,
        "id": mistake.get("id") or uuid.uuid4().hex[:12],
        "created_at": mistake.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    mistakes.append(record)
    _write_json(MISTAKES_FILE, mistakes)
    return record


def delete_mistake(mistake_id):
    """按 id 删除错题，返回是否删除成功。"""
    mistakes = load_mistakes()
    remain = [m for m in mistakes if m.get("id") != mistake_id]
    changed = len(remain) != len(mistakes)
    if changed:
        _write_json(MISTAKES_FILE, remain)
    return changed


def update_mistake(mistake_id, data):
    """按 id 更新错题的部分字段（data 为要合并的字段 dict），返回是否更新成功。"""
    mistakes = load_mistakes()
    changed = False
    for m in mistakes:
        if m.get("id") == mistake_id:
            m.update(data)
            changed = True
    if changed:
        _write_json(MISTAKES_FILE, mistakes)
    return changed


def save_mistake_image(image_bytes, mistake_id):
    """
    保存错题原图到 data/images/<id>.jpg，返回保存路径；失败返回 None。

    参数:
        image_bytes: bytes，图片原始字节。
        mistake_id: str，错题 id，用作文件名。
    """
    try:
        os.makedirs(IMAGE_DIR, exist_ok=True)
        path = os.path.join(IMAGE_DIR, f"{mistake_id}.jpg")
        with open(path, "wb") as f:
            f.write(image_bytes)
        return path
    except OSError:
        return None


# ============================ 画像对话历史 ============================
def load_conversation():
    """读取画像对话历史；不存在时返回空列表。"""
    data = _read_json(CONVERSATION_FILE, [])
    return data if isinstance(data, list) else []


def save_conversation(messages):
    """保存画像对话历史（整体覆盖写入）。"""
    _write_json(CONVERSATION_FILE, messages)
