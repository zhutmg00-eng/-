# 碳资产管理与智能合规决策助手

面向物流企业的碳资产管理工具 — 碳排放基线测算 + 碳交易政策智能顾问

## 快速开始

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API 密钥

# 4. 启动后端 API
uvicorn src.api.main:app --reload --port 8000

# 5. 启动前端（新终端）
streamlit run src/ui/app.py
```

## 项目结构

```
carbon-asset-assistant/
├── data/                    # 数据目录（不提交Git）
│   ├── raw/                 # 原始数据
│   ├── processed/           # 清洗后数据
│   ├── policy_docs/         # 政策文档
│   └── chroma_db/           # 向量数据库
├── src/
│   ├── config.py            # 全局配置
│   ├── models/             # 数据模型（Pydantic）
│   ├── engine/              # 碳排放计算引擎
│   ├── rag/                 # RAG政策解析助手
│   ├── api/                 # FastAPI接口
│   └── ui/                  # Streamlit前端
├── tests/                   # 测试
├── docs/                    # 文档
└── notebooks/               # Jupyter实验笔记
```

## 团队

- 陈铭浩（负责人）— 系统架构、RAG、API开发
- 张可为 — 文献综述、碳配额规则、验证
- 王逸贤 — 排放因子数据、代码实现、测试

## 技术栈

Python 3.10+ · FastAPI · Streamlit · LangChain · ChromaDB · Pandas · Plotly
