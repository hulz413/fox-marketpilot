## 为什么

MarketPilot 需要先建立清晰的项目仓库骨架，后续 P0 业务切片才能在稳定的位置上推进前端、后端、本地依赖服务、部署根目录和 OpenSpec 任务。

这次骨架采用 MVP 阶段更直观的结构：`frontend/` 放 Vercel 部署的 Next.js 应用，`backend/` 放 Railway 部署的 FastAPI/Celery 应用，根目录 `infra/` 放本地依赖服务配置。

## 变更内容

- 新增顶层 `frontend/`、`backend/` 和 `infra/` 目录。
- 在 `frontend/` 下新增 Next.js + TypeScript 前端骨架，包含 Tailwind CSS、shadcn/ui 配置、App Router 结构，以及 research、opportunities、reports 等 feature 占位。
- 在 `backend/` 下新增 FastAPI 后端骨架，包含 API 路由、配置、数据库、外部集成、Agent 编排、Celery worker 和 MVP 业务模块边界。
- 在根目录 `infra/` 下新增本地依赖服务配置，仅覆盖 Docker 管理的 PostgreSQL + pgvector、Redis 和 MinIO。
- 新增环境变量示例和开发文档，说明本地启动方式和线上部署 root directory 约定。
- 不新增应用 Dockerfile，也不把前端、FastAPI、Celery 或 LangGraph 进程放入 Docker Compose；应用进程本地运行在宿主机，线上走平台源码部署。

## 能力

### 新增能力

- `project-skeleton`: 定义 MarketPilot 初始代码库的仓库布局、应用骨架、本地依赖服务、环境变量示例和验证要求。

### 修改能力

- 无。

## 影响

- 影响仓库区域：`frontend/`、`backend/`、`infra/`、`README.md` 和环境变量示例文件。
- 影响本地运行方式：Next.js、FastAPI、Celery 和 LangGraph 相关进程在宿主机运行；Docker Compose 仅启动 PostgreSQL、Redis 和 MinIO。
- 影响线上部署约定：Vercel 使用 `frontend/` 作为 root directory；Railway Web Service 和 Worker Service 使用 `backend/` 作为 root directory。
- 影响依赖基线：引入所选技术栈需要的前端和后端包配置、脚本和基础校验入口。
