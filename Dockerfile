# ============================================================
# 碳资产助手 — Docker 多阶段构建
#
# 阶段1 (builder): 安装系统依赖和Python依赖
# 阶段2 (runtime): 运行FastAPI和Streamlit
# ============================================================

# ---- 构建阶段 ----
FROM python:3.11-slim AS builder

# 安装中文字体（用于报告生成）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    fonts-wqy-zenhei \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- 运行阶段 ----
FROM python:3.11-slim AS runtime

# 安装中文字体
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    fonts-wqy-zenhei \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制Python包
COPY --from=builder /install /usr/local

# 设置工作目录
WORKDIR /app

# 复制项目代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data/raw /app/data/processed /app/data/policy_docs /app/data/chroma_db

# 暴露端口
# 8000 — FastAPI API服务
# 8501 — Streamlit Web UI
EXPOSE 8000 8501

# 环境变量（支持运行时配置）
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 默认启动命令（通过docker-compose指定）
CMD ["echo", "请通过 docker compose up 启动服务"]
