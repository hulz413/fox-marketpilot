## 1. 仓库结构

- [x] 1.1 创建顶层 `frontend/`、`backend/` 和 `infra/` 目录。
- [x] 1.2 确保 `frontend/` 是唯一前端应用根目录，`backend/` 是唯一后端应用根目录。
- [x] 1.3 仅在空目录无法被保留时添加最小占位文件。

## 2. 前端骨架

- [x] 2.1 将 `frontend/` 初始化为使用 App Router、`src/app`、Tailwind CSS、ESLint 和 npm scripts 的 Next.js TypeScript 应用。
- [x] 2.2 配置 TypeScript path aliases，使 `@/*` 指向 `frontend/src/*`。
- [x] 2.3 添加 shadcn/ui 基础配置，包括 `frontend/components.json`、CSS variables、本地 aliases 和 lucide icon library。
- [x] 2.4 添加 TanStack Query、React Hook Form、Zod、Recharts、shadcn/ui 支撑包和 SSE client integration 所需的前端基础依赖。
- [x] 2.5 创建 `frontend/src/components/ui`、`frontend/src/hooks`、`frontend/src/lib` 和 `frontend/src/features` 结构。
- [x] 2.6 创建 `research`、`opportunities` 和 `reports` 前端 feature 占位，不实现产品行为。
- [x] 2.7 添加 `frontend/.env.example`，说明本地 API 和 SSE 配置值。

## 3. 后端骨架

- [x] 3.1 将 `backend/` 初始化为 Python project，包含 `pyproject.toml`、无需 npm 的后端脚本或文档化 Python 命令，以及测试工具。
- [x] 3.2 添加 FastAPI、Uvicorn、Pydantic settings、SQLAlchemy、Alembic、PostgreSQL access、Celery、Redis、LangGraph、LangSmith、OpenAI-compatible SDK access、Tavily、Playwright、boto3 和测试所需后端依赖。
- [x] 3.3 创建包含最小 FastAPI application 和 health route 的 `backend/app/main.py`。
- [x] 3.4 创建 `api`、`core`、`db`、`integrations`、`agents`、`workers` 和 `modules` 后端 packages。
- [x] 3.5 创建 `backend/app/api/v1` router 结构，并从 FastAPI application 注册。
- [x] 3.6 创建 `research_tasks`、`opportunities`、`sources` 和 `reports` 领域占位，不实现产品行为。
- [x] 3.7 创建 LLM provider access、Tavily、S3-compatible object storage 和 LangSmith tracing 集成占位，不要求真实外部凭证。
- [x] 3.8 添加 Celery application 和 worker entrypoint 占位，允许在不执行真实研究任务的情况下启动。
- [x] 3.9 添加 Alembic 基础配置和 database package 占位。
- [x] 3.10 添加 `backend/.env.example`，说明 database、Redis、object storage、LangSmith、Tavily、DeepSeek 和 OpenAI-compatible provider settings。

## 4. 本地基础设施

- [x] 4.1 添加根目录 `infra/compose.yaml`，仅包含支持 pgvector 的 PostgreSQL、Redis 和 MinIO。
- [x] 4.2 添加 `infra/.env.example`，包含本地端口、用户名、密码、bucket names 和非生产默认值。
- [x] 4.3 验证 Compose 文件不定义 frontend、FastAPI、Celery 或 LangGraph application containers。

## 5. 文档

- [x] 5.1 更新 `README.md`，说明仓库结构和目录职责。
- [x] 5.2 文档化从 `infra/` 启动本地依赖服务的方式。
- [x] 5.3 文档化 frontend install、dev、lint、typecheck 和 build 命令。
- [x] 5.4 文档化 backend virtualenv、install、test、API dev server 和 Celery worker 命令。
- [x] 5.5 文档化 Vercel 和 Railway 的 deployment root 约定。
- [x] 5.6 文档化可观测性相关环境变量，尤其是 LangSmith tracing settings 和 task trace linkage expectations。

## 6. 验证

- [x] 6.1 运行 frontend baseline validation commands，并修复 scaffold 问题。
- [x] 6.2 运行 backend baseline validation commands，并修复 scaffold 问题。
- [x] 6.3 验证 local Compose configuration syntax。
- [x] 6.4 确认 scaffold checks 不需要真实 Tavily、DeepSeek、LangSmith 或 object storage production credentials。
- [x] 6.5 确认生成文件满足 `project-skeleton` 的 OpenSpec requirements。
