<<<<<<< HEAD
🎓 智学伴侣 — AI 个性化学习伴侣（本地网页版）

面向高中生和大学生的本地运行「AI 个性化学习伴侣」。拍照上传错题让 AI 分析错因、详细解析并生成变式题；通过自然对话构建你的专属学习画像；再根据画像推送定制化学习资源。



✨ 核心功能

功能	说明

📸 AI 错题本与举一反三	上传错题照片（或手动输入题目），AI 自动识别题目、分析错误原因、给出一步步的详细解析，并生成 3-5 道同类型变式题（附答案与提示）

👤 对话式学习画像	像聊天一样告诉 AI 你的学段、目标、薄弱点和习惯，AI 自动提炼成结构化学习画像；也支持表单手动编辑

📚 个性化资源推荐	根据画像中的薄弱点、目标与每日可用时间，推荐视频 / 文章 / 练习类学习资源

🧪 演示模式

未配置 API Key 时，程序自动进入演示模式：所有 AI 回复均为内置模拟数据（含一道完整的二次函数错题分析示例），无需联网、无需真实调用接口，即可体验全部页面和完整流程。配置 API Key 后重启即切换为真实 AI 调用。



🛠 技术栈

Python 3.10+

Streamlit（网页界面）

openai 官方 SDK（OpenAI 兼容接口）

python-dotenv（环境变量管理）

Pillow（图片压缩处理）

JSON 文件本地存储（data/ 目录，无需数据库）

📦 安装依赖

bash

\# 1.（可选但推荐）创建并激活虚拟环境

python -m venv .venv

\# Windows 激活：

.venv\\Scripts\\activate

\# macOS / Linux 激活：

source .venv/bin/activate



\# 2. 安装依赖

pip install -r requirements.txt

⚙️ 配置 .env

项目根目录已自带 .env 模板（默认全部注释，即演示模式）。需要真实 AI 时，编辑 .env 取消注释并填入你的配置：



env

\# OpenAI API 密钥（必填）

OPENAI\_API\_KEY=sk-xxxxxxxxxxxxxxxx



\# OpenAI 兼容接口地址（可选，默认官方地址；用第三方/本地服务时修改）

OPENAI\_BASE\_URL=https://api.openai.com/v1



\# 多模态模型名（错题图片识别用）

MODEL\_NAME=gpt-4o-mini



\# 对话模型名（聊天 / 画像提取 / 资源推荐用；不填则复用 MODEL\_NAME）

CHAT\_MODEL\_NAME=gpt-4o-mini

兼容所有 OpenAI 兼容接口（如各类中转服务、本地部署的 vLLM/Ollama 等），只需修改 OPENAI\_BASE\_URL。



🚀 运行

bash

streamlit run app.py

浏览器会自动打开 http://localhost:8501（若未自动打开请手动访问）。



📁 目录结构

ai\_learning\_companion/

├── app.py              # Streamlit 主程序（四个页面）

├── utils/

│   ├── \_\_init\_\_.py

│   ├── llm.py          # 大模型调用封装 + 演示模式模拟数据

│   ├── prompts.py      # 四类提示词模板

│   └── storage.py      # 本地 JSON 数据存储

├── data/               # 自动生成：画像 / 错题本 / 对话历史 / 错题图片

├── .env                # 环境变量配置（未配置即演示模式）

├── requirements.txt

└── README.md

💾 数据说明

所有数据保存在本地 data/ 目录，不会上传到任何服务器：



data/profile.json — 学生画像

data/mistakes.json — 错题本

data/conversation.json — 画像对话历史

data/images/ — 错题原图

=======
# ai-liaoweiqi
>>>>>>> e02fda205dcf6e11d465483d0f35c0429c37e4a5
