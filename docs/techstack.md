# MarketPilot MVP 技术栈

## 技术选型

### 前端

| 模块     | 技术                       |
| ------ | ------------------------ |
| Web 框架 | Next.js + TypeScript     |
| UI     | Tailwind CSS + shadcn/ui |
| 数据请求   | TanStack Query           |
| 表单     | React Hook Form + Zod    |
| 图表     | Recharts                 |
| 流式进度   | SSE                      |
| 部署     | Vercel                   |

### 后端

| 模块       | 技术             |
| -------- | -------------- |
| API 服务   | FastAPI        |
| Agent 编排 | LangGraph      |
| 异步任务     | Celery + Redis |
| 数据校验     | Pydantic       |
| ORM      | SQLAlchemy     |
| 数据库迁移    | Alembic        |
| 部署       | Railway        |

### 搜索与提取

| 模块         | 技术                          |
| ---------- | --------------------------- |
| Web Search | Tavily                      |
| 网页正文提取     | Tavily Extract + Playwright |
| 浏览器自动化     | Playwright                  |

### 数据存储

| 模块         | 本地                | 线上                      |
| ---------- | ----------------- | ----------------------- |
| PostgreSQL | Docker PostgreSQL | Railway Postgres        |
| 向量检索       | pgvector          | pgvector                |
| Redis      | Docker Redis      | Railway Redis           |
| 对象存储       | Docker MinIO      | Railway Storage Buckets |

对象存储统一走 S3-compatible SDK，例如 `boto3`。

### 大模型

| 模块           | 技术                         |
| ------------ | -------------------------- |
| Provider 抽象  | OpenAI-compatible provider |
| MVP Provider | DeepSeek API               |
| SDK          | OpenAI Python SDK          |
| Base URL     | `https://api.deepseek.com` |

### 可观测性

| 模块            | 技术                                   |
| ------------- | ------------------------------------ |
| Agent tracing | LangSmith                            |
| RAG tracing   | LangSmith trace + retrieval metadata |
| 评测集管理         | LangSmith Datasets                   |
| RAG 评测        | LangSmith Evaluation                 |
| 应用日志          | Python logging + Railway logs        |

LangSmith 通过环境变量启用 tracing，例如 `LANGSMITH_TRACING=true`、`LANGSMITH_API_KEY` 和 `<mark>LANGSMITH_PROJECT</mark>`。

## 运行方式

### 本地开发

主程序不使用 Docker，依赖服务使用 Docker。

| 进程/服务             | 运行方式           |
| ----------------- | -------------- |
| FastAPI API       | 本机 Python      |
| Celery worker     | 本机 Python      |
| LangGraph runtime | 本机 Python      |
| PostgreSQL        | Docker Compose |
| Redis             | Docker Compose |
| MinIO             | Docker Compose |

### 线上部署

线上不维护 Dockerfile，也不使用 docker compose。应用使用平台源码部署，依赖服务使用托管服务。

| 服务             | 部署方式                    |
| -------------- | ----------------------- |
| Frontend       | Vercel                  |
| FastAPI API    | Railway Web Service     |
| Celery worker  | Railway Worker Service  |
| PostgreSQL     | Railway Postgres        |
| Redis          | Railway Redis           |
| Object Storage | Railway Storage Buckets |
