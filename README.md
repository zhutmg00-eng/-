# 碳资产管理与智能合规决策助手

> 面向物流企业的碳资产管理工具 — 碳排放基线测算 + 碳交易政策智能顾问

## 项目简介

本项目是一个面向物流运输企业的碳资产管理工具，帮助企业完成：
1. **碳排放基线测算** — 输入车队参数，输出年度碳排放量、配额缺口、预估合规成本
2. **碳交易政策智能问答** — 基于RAG技术，用自然语言查询碳交易政策法规
3. **碳资产可视化看板** — Streamlit前端展示企业碳资产全景

## 快速开始

### 环境要求

- Python 3.10+
- 网络连接（用于下载依赖和调用LLM API）

### 安装步骤

```bash
# 1. 克隆/解压项目
tar xzf carbon-asset-assistant-phase1-complete.tar.gz
cd carbon-asset-assistant

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API 密钥（至少配置一个LLM API key）

# 5. 运行测试（验证安装成功）
python3 -m pytest tests/test_calculator.py tests/test_api.py -v
# 预期输出: 25 passed

# 6. 启动后端 API
uvicorn src.api.main:app --reload --port 8000

# 7. 启动前端（新终端）
streamlit run src/ui/app.py
```

### 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API密钥（推荐，性价比最高） | 空 |
| `DASHSCOPE_API_KEY` | 阿里通义千问API密钥 | 空 |
| `ZHIPU_API_KEY` | 智谱GLM API密钥 | 空 |
| `OPENAI_API_KEY` | OpenAI API密钥（用于Embedding） | 空 |
| `LLM_MODEL` | 默认使用的模型 | `deepseek-chat` |
| `CORS_ORIGINS` | CORS允许的前端来源（逗号分隔） | `http://localhost:8501,http://localhost:3000` |
| `APP_API_KEY` | API鉴权密钥（留空=开发模式不鉴权） | 空 |

## 项目结构

```
carbon-asset-assistant/
├── data/                        # 数据目录
│   ├── raw/                     # 原始数据
│   │   ├── emission_factors.csv       # 排放因子数据库（19条）
│   │   ├── carbon_price_history.csv   # 碳价历史数据（274条）
│   │   ├── emission_factors_research.json  # 排放因子研究来源
│   │   ├── carbon_price_sources.json        # 碳价数据来源
│   │   ├── literature_review_raw.json      # 18篇文献数据
│   │   └── policy_docs_catalog.json         # 政策文档目录
│   ├── policy_docs/             # 政策文档库（37份，412KB）
│   └── chroma_db/               # ChromaDB向量数据库（运行时生成）
├── src/
│   ├── config.py                # 全局配置
│   ├── models/                  # 数据模型（Pydantic）
│   │   ├── fleet.py             # 车队模型
│   │   ├── carbon.py            # 碳排放结果模型
│   │   └── policy.py            # 政策问答模型
│   ├── engine/                  # 碳排放计算引擎
│   │   ├── emission_factors.py  # 排放因子数据库（CSV加载+内置fallback）
│   │   ├── calculator.py        # 碳排放基线计算
│   │   ├── quota.py             # 配额缺口估算
│   │   ├── carbon_price.py      # 碳价参考与成本预测
│   │   └── __init__.py          # 引擎统一导出
│   ├── rag/                     # RAG政策解析助手（自研链路）
│   │   ├── crawler.py           # 政策文档爬取
│   │   ├── parser.py            # 文档解析(PDF/DOCX/HTML) + 清洗 + 切分
│   │   ├── vector_store.py      # 向量知识库（ChromaDB优先，TF-IDF fallback）
│   │   ├── generator.py         # Prompt模板 + LLM调用（含错误处理）
│   │   └── __init__.py          # RAG统一入口（PolicyAdvisor）
│   ├── api/                     # FastAPI后端
│   │   └── main.py              # API入口（含CORS、鉴权、路径校验）
│   └── ui/                      # Streamlit前端
│       └── app.py               # 主入口（5个页面）
├── tests/                       # 测试
│   ├── test_calculator.py       # 计算引擎测试（20个）
│   ├── test_api.py              # API测试（5个）
│   └── test_rag.py              # RAG测试
├── scripts/                     # 工具脚本
│   ├── e2e_demo.py              # 端到端演示
│   ├── test_rag_pipeline.py     # RAG链路测试
│   ├── ingest_policy_docs.py    # 政策文档入库脚本
│   ├── download_attachments.py  # PDF附件下载
│   ├── fetch_mee_pages.py       # 生态环境部页面抓取
│   └── baidu_search.py          # 百度搜索辅助脚本
├── docs/                        # 文档
│   ├── architecture.md          # 系统架构文档
│   ├── literature_review.md     # 文献综述（18篇，24KB）
│   ├── 开题报告.md              # 开题报告（22KB）
│   └── code_review_report.md   # 代码审查报告（543行）
├── requirements.txt             # Python依赖
├── .env.example                 # 环境变量模板
├── .gitignore                   # Git忽略规则
└── README.md                    # 本文件
```

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端API | FastAPI | 高性能异步框架，自动生成OpenAPI文档 |
| 前端 | Streamlit | 快速原型开发，适合数据应用 |
| 计算引擎 | Python标准库 | 纯Python实现，无额外依赖 |
| RAG链路 | 自研 | parser→vector_store→generator，不依赖LangChain |
| 向量数据库 | ChromaDB | 本地持久化，支持语义检索（可选，未安装时降级为TF-IDF） |
| 数据模型 | Pydantic v2 | 类型安全，自动校验 |
| PDF解析 | PyMuPDF | 高性能PDF文本提取 |
| LLM | DeepSeek/Qwen/GLM | 国产模型优先，通过OpenAI兼容接口调用 |

## API接口

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/health` | 健康检查 | 否 |
| GET | `/api/vehicle-types` | 获取支持的车型列表 | 是 |
| POST | `/api/calculate` | 计算碳排放基线+配额+成本 | 是 |
| POST | `/api/ask` | 碳交易政策智能问答 | 是 |
| GET | `/api/kb/stats` | 知识库统计 | 是 |
| POST | `/api/kb/ingest` | 导入政策文档到知识库 | 是 |

## 核心计算公式

### 碳排放基线
```
E = Σ (n_i × d_i × EF_i × LF_i) / 1000

  n_i  = 第i类车型数量（辆）
  d_i  = 年均运营里程（km/年）
  EF_i = CO₂排放因子（kgCO₂/km）
  LF_i = 满载率调整系数 = 1 + 0.15×(0.75 - l_i)
```

### 配额缺口
```
Gap = E - Q
Q = Σ (n_i × q_benchmark_i × adjustment_factor)

  q_benchmark = 行业基准值（tCO₂/辆/年），原型验证用估算值
```

### 碳合规成本
```
Cost = max(Gap, 0) × P_current
Cost_low  = max(Gap, 0) × P_min(近90日)
Cost_high = max(Gap, 0) × P_max(近90日)
```

## 数据资产

| 数据集 | 记录数 | 来源 |
|--------|--------|------|
| 排放因子 | 19条 | 蔡博峰等(2021)中国环境科学 + GB 30510-2024 |
| 碳价历史 | 274条 | 上海环交所周度数据（73真实+201插值） |
| 政策文档 | 37份 | 生态环境部、国务院、交通运输部等 |
| 文献数据 | 18篇 | 交通碳排放、碳交易、RAG三个方向 |

## 团队

- **陈铭浩**（负责人）— 系统架构、RAG、API开发
- **张可为** — 文献综述、碳配额规则、验证
- **王逸贤** — 排放因子数据、代码实现、测试
- **汪晓霞**（指导教师）— 技术指导

## 测试

```bash
# 运行全部测试
python3 -m pytest tests/ -v

# 运行端到端演示
python3 scripts/e2e_demo.py

# 运行RAG链路测试
python3 scripts/test_rag_pipeline.py
```

## 许可证

本项目为大学生创新创业训练计划项目，仅供学术研究使用。
