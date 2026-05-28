## ADDED Requirements

### Requirement: 仓库结构分离前端、后端和本地基础设施

仓库 SHALL 提供顶层 `frontend/`、`backend/` 和 `infra/` 目录，并明确三者职责。

#### Scenario: 查看顶层目录

- **WHEN** 开发者在应用骨架生成后查看仓库根目录
- **THEN** 根目录包含 `frontend/`、`backend/` 和 `infra/`
- **AND** `frontend/` 包含 Next.js 应用骨架
- **AND** `backend/` 包含 FastAPI 应用骨架
- **AND** `infra/` 包含本地依赖服务配置

#### Scenario: 部署根目录明确

- **WHEN** 开发者阅读项目 setup 文档
- **THEN** 文档标明 `frontend/` 是 Vercel root directory
- **AND** 文档标明 `backend/` 是 Railway Web Service 和 Worker Service 的 root directory

### Requirement: 前端骨架支持选定的 MVP Web 技术栈

`frontend/` 应用 SHALL 为 Next.js、TypeScript、Tailwind CSS、shadcn/ui、TanStack Query、React Hook Form、Zod、Recharts 和 SSE client integration points 提供骨架。

#### Scenario: 查看前端应用结构

- **WHEN** 开发者查看 `frontend/`
- **THEN** 它包含 Next.js TypeScript 项目所需的应用级配置文件
- **AND** 它使用 `src/app` 放置 App Router 源码
- **AND** 它包含用于 shadcn/ui 组件的 `src/components/ui`
- **AND** 它包含 `src/lib`、`src/hooks` 和 `src/features`

#### Scenario: 查看前端 feature 占位

- **WHEN** 开发者查看 `frontend/src/features`
- **THEN** 它包含 `research`、`opportunities` 和 `reports` 占位
- **AND** 这些占位可供后续 P0 changes 使用，但本 change 不实现产品行为

#### Scenario: 查看 shadcn/ui 配置

- **WHEN** 开发者打开 `frontend/components.json`
- **THEN** 它配置 TypeScript 支持
- **AND** 它映射 components、UI components、utilities、library code 和 hooks aliases
- **AND** 它配置 Tailwind CSS variables
- **AND** 它使用 lucide icon library

### Requirement: 后端骨架支持选定的 MVP API 和 Agent 技术栈

`backend/` 应用 SHALL 为 FastAPI、LangGraph、Celery、Redis、Pydantic、SQLAlchemy、Alembic、PostgreSQL、pgvector、S3-compatible 对象存储、Tavily、Playwright、OpenAI-compatible LLM access 和 LangSmith tracing integration points 提供骨架。

#### Scenario: 查看后端应用结构

- **WHEN** 开发者查看 `backend/`
- **THEN** 它包含 Python project configuration file
- **AND** 它包含作为 FastAPI application entrypoint 的 `app/main.py`
- **AND** 它包含 `api`、`core`、`db`、`integrations`、`agents`、`workers` 和 `modules` packages
- **AND** 它包含用于数据库迁移的 `alembic` 目录
- **AND** 它包含用于后端测试的 `tests` 目录

#### Scenario: 查看后端领域占位

- **WHEN** 开发者查看 `backend/app/modules`
- **THEN** 它包含 `research_tasks`、`opportunities`、`sources` 和 `reports` 占位
- **AND** 这些占位可供后续 P0 changes 使用，但本 change 不实现产品行为

#### Scenario: 查看后端集成占位

- **WHEN** 开发者查看 `backend/app/integrations`
- **THEN** 它包含 LLM provider、Tavily、S3-compatible object storage 和 LangSmith tracing 占位
- **AND** 这些占位在骨架验证时不需要真实外部凭证

### Requirement: 本地依赖服务隔离在根目录 infra 下

仓库 SHALL 在根目录提供本地依赖服务配置，并且 SHALL NOT 引入应用 Dockerfile 或 Docker Compose application services。

#### Scenario: 查看本地 Compose 配置

- **WHEN** 开发者打开 `infra/` 下的本地 Compose 文件
- **THEN** 它定义支持 pgvector 的 PostgreSQL
- **AND** 它定义 Redis
- **AND** 它定义 MinIO 或 S3-compatible local object storage
- **AND** 它不定义 frontend、FastAPI、Celery 或 LangGraph application containers

#### Scenario: 查看应用 Docker 产物

- **WHEN** 开发者搜索 scaffold 中的 application Dockerfiles
- **THEN** scaffold 不要求 frontend 或 backend application Dockerfile
- **AND** 本地应用启动方式被文档化为宿主机进程

### Requirement: 环境变量示例说明本地和部署配置

Scaffold SHALL 包含 frontend、backend 和 local infrastructure 的环境变量示例文件。

#### Scenario: 查看前端环境变量示例

- **WHEN** 开发者打开 frontend environment example
- **THEN** 它说明 frontend 需要的 public backend API base URL
- **AND** 它说明本地 SSE/API 通信需要的配置值

#### Scenario: 查看后端环境变量示例

- **WHEN** 开发者打开 backend environment example
- **THEN** 它说明 database、Redis、object storage、LangSmith、Tavily 和 OpenAI-compatible LLM provider settings
- **AND** 它包含 MVP provider configuration 期望的 DeepSeek base URL

#### Scenario: 查看基础设施环境变量示例

- **WHEN** 开发者打开 infrastructure environment example
- **THEN** 它说明本地 PostgreSQL、Redis 和 MinIO 端口与凭证
- **AND** 它不包含生产 secret values

### Requirement: 骨架验证方式被文档化

仓库 SHALL 说明如何从 clean checkout 验证项目骨架。

#### Scenario: 阅读本地 setup 说明

- **WHEN** 开发者阅读 scaffold 后的仓库 README
- **THEN** 它说明如何安装 frontend dependencies
- **AND** 它说明如何安装 backend dependencies
- **AND** 它说明如何启动本地依赖服务
- **AND** 它说明如何运行 frontend、backend API 和 backend worker processes

#### Scenario: 运行 baseline checks

- **WHEN** 开发者执行文档中的 validation commands
- **THEN** frontend baseline check 可以在没有真实外部 API credentials 的情况下独立运行
- **AND** backend baseline check 可以在没有真实外部 API credentials 的情况下独立运行
