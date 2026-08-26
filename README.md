# 物流碳排放与减排情景决策助手

> 面向物流运输企业的大学生创新训练科研原型：直接运营排放核算、减排情景分析与政策资料检索。

## 项目定位

本项目输入车型、车辆数、年均里程和满载率，输出车辆直接运营排放基线，并通过模拟碳预算比较不同减排情景。政策助手使用本地政策知识库检索相关原文；配置 LLM 后可在检索内容范围内生成分析，未配置时返回带来源的原文摘录。

本项目适合作为大创项目的前提，是将研究重点放在“物流企业排放核算与政策检索方法验证”，而不是宣称已经提供法定碳资产管理或履约服务。

> 重要边界：物流运输行业目前未纳入全国碳市场配额管理。系统中的模拟碳预算、预算差额、情景成本和潜在价值仅用于科研比较，不代表法定配额、履约义务、可交易资产或实际收益。新能源物流车当前仅按直接运营排放为零核算，未计购电间接排放及车辆全生命周期排放。

## 当前功能

- 车队直接运营排放核算，支持 6 类内置车型及 CSV 扩展
- 模拟碳预算差额与碳价对标情景
- 新能源替代、满载率提升和组合减排情景
- ChromaDB 语义召回与中文标题/关键词混合重排
- PDF、DOCX、HTML、Markdown、TXT 政策文档解析与网页噪声清洗
- 无 LLM 密钥时的可追溯检索式回答
- FastAPI、Streamlit、PDF 报告、多企业对比和 Docker Compose 部署
- 输入边界校验、API Key、CORS、路径范围校验和自动化测试

## 快速开始

要求 Python 3.10 及以上版本。

```powershell
git clone https://github.com/zhutmg00-eng/-.git carbon-logistics-assistant
cd carbon-logistics-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pytest -q
```

启动后端和前端：

```powershell
# 终端 1
uvicorn src.api.main:app --reload --port 8000

# 终端 2
streamlit run src/ui/app.py
```

- Web：`http://localhost:8501`
- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/health`

开发环境不设置 `APP_API_KEY` 时，API 进入无鉴权模式。设置密钥后，前端和请求方都需发送同一 `X-API-Key`。

## Docker

```powershell
# 开发环境，默认使用 dev-key
docker compose up --build

# 生产覆盖配置
Copy-Item .env.example .env
# 修改 .env 中 APP_API_KEY 和 CORS_ORIGINS
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

生产配置要求显式提供 `APP_API_KEY` 和 `CORS_ORIGINS`，并保持 Streamlit XSRF 防护开启。

## 环境变量

| 变量 | 用途 | 默认值 |
|---|---|---|
| `APP_API_KEY` | FastAPI 与 Streamlit 间的共享密钥 | 空，开发模式不鉴权 |
| `API_BASE_URL` | Streamlit 调用的后端地址 | `http://localhost:8000` |
| `CORS_ORIGINS` | 允许的浏览器来源，逗号分隔 | 本地地址 |
| `LLM_MODEL` | 政策分析模型 | `deepseek-chat` |
| `DEEPSEEK_API_KEY` | DeepSeek 密钥，可选 | 空 |
| `DASHSCOPE_API_KEY` | 通义千问密钥，可选 | 空 |
| `ZHIPU_API_KEY` | 智谱密钥，可选 | 空 |
| `OPENAI_API_KEY` | OpenAI LLM 或 Embedding 密钥，可选 | 空 |
| `EMBEDDING_MODEL` | Chroma 嵌入函数 | `chromadb-default` |

`EMBEDDING_MODEL` 可设为 `chromadb-default`、`openai:text-embedding-3-small`、`bge-local` 或 `sentence-transformers:<model>`。OpenAI 模式必须同时设置 `OPENAI_API_KEY`。

## 项目结构

```text
.
├── data/
│   ├── raw/                    # 排放因子、碳价与研究来源
│   ├── policy_docs/            # 政策 Markdown 文档
│   ├── chroma_db/              # 运行时生成，不提交
│   └── reports/                # 示例及运行时 PDF
├── docs/                       # 架构、文献、开题和审查资料
├── scripts/
│   ├── e2e_demo.py             # 计算链路端到端演示
│   ├── ingest_policy_docs.py   # 政策知识库入库
│   └── test_rag_pipeline.py    # RAG 相关性验收
├── src/
│   ├── api/                    # FastAPI 与多企业对比
│   ├── engine/                 # 排放、预算、碳价和减排引擎
│   ├── models/                 # Pydantic 输入模型
│   ├── rag/                    # 解析、混合检索与生成
│   └── ui/                     # Streamlit 与 PDF 报告
├── tests/                      # 61 项自动化测试
├── Dockerfile
└── docker-compose.yml
```

## API

| 方法 | 路径 | 说明 | 鉴权 |
|---|---|---|---|
| GET | `/api/health` | 健康检查 | 否 |
| GET | `/api/vehicle-types` | 支持车型和排放因子 | 是 |
| POST | `/api/calculate` | 直接运营排放、模拟预算和情景成本 | 是 |
| POST | `/api/compare` | 多企业情景对比 | 是 |
| POST | `/api/ask` | 政策检索与问答 | 是 |
| GET | `/api/kb/stats` | 知识库状态 | 是 |
| POST | `/api/kb/ingest` | 导入 `data/policy_docs` 内文档 | 是 |

无效车辆数、里程、满载率、企业名、空车队和未知车型统一返回 `422`。

## 计算口径

直接运营排放：

```text
E = sum(n_i * d_i * EF_i * LF_i) / 1000
```

- `n_i`：车型数量
- `d_i`：年均运营里程
- `EF_i`：车辆直接排放因子
- `LF_i`：低满载率调整系数

模拟碳预算差额（默认减排目标 `r_target=10%`，页面可调整）：

```text
Gap = E - B
B = sum(n_i * EF_i * d_reference_i * (1 - r_target)) / 1000
```

`B` 由排放因子、参考年均里程和用户选择的情景减排目标直接计算，可复算并用于敏感性分析；内部计算保留原始精度，仅在最终响应和展示时四舍五入。它不是官方分配的免费配额或政策目标。情景金额使用全国碳市场历史价格作对标，不能解释为物流企业当前履约成本或确定收益。CSV 中标为全生命周期或区域电网情景的电动车因子不会进入直接运营车型列表。

## 验证

```powershell
python -m pytest -q
python scripts\e2e_demo.py
python scripts\test_rag_pipeline.py
```

RAG 验收包含两项硬性相关性断言：

- “物流运输工具碳排放怎么核算”首条命中运输工具核算方法
- “交通运输行业碳达峰目标”首条命中交通运输碳达峰实施方案

PDF 测试会检查预算字段、科研免责声明、新能源核算边界、页码和字体兼容单位。

`docs/ci-workflow-template.yml` 是尚未激活的 GitHub Actions 模板。启用时需将其移入 `.github/workflows/`，并使用具有 `workflow` 权限的 GitHub 凭据推送；只有远端实际运行通过后才能宣称 CI 已启用。

## 下一阶段研究重点

1. 获取匿名化真实车队或公开统计样本，比较模型结果与企业燃料台账/标准方法结果。
2. 建立 30 至 50 道带标准来源和适用范围标签的政策问题集，比较纯向量、关键词和混合检索。
3. 报告 Recall@k、MRR、来源准确率、适用范围判断准确率和回答忠实度，不只展示案例。
4. 将购电间接排放、运输周转量和不确定性区间纳入模型，并对排放因子和满载率参数做敏感性分析。
5. 让指导教师、物流企业人员或相关专业教师进行盲评，保留评价表和迭代记录作为结题证据。

## 许可

本项目为大学生创新创业训练计划科研原型，仅供教学和研究使用。
