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
