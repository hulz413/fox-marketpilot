## 背景

MarketPilot 当前是文档优先的仓库，已有 `docs/techstack.md`、`docs/mvp/roadmap.md` 和 OpenSpec 配置，但还没有应用代码骨架。MVP roadmap 中的多个 P0 切片会共同依赖研究任务、异步执行、进度展示、商机推荐、详情、报告和可观测性基础。

技术栈已经将产品拆成 Vercel 承载的 Next.js 前端，以及 Railway 承载的 FastAPI 后端和 Celery worker。本地开发时，应用进程运行在宿主机；Docker Compose 只负责 PostgreSQL + pgvector、Redis 和 MinIO 等依赖服务。

## 目标 / 非目标

**目标：**

- 建立直接、易读的顶层结构：`frontend/`、`backend/` 和根目录 `infra/`。
- 让部署根目录一眼明确：Vercel 指向 `frontend/`，Railway Web Service 和 Worker Service 指向 `backend/`。
- 提供匹配 Next.js App Router、TypeScript、Tailwind CSS、shadcn/ui、TanStack Query、React Hook Form、Zod、Recharts 和 SSE 进度能力的前端骨架。
- 提供匹配 FastAPI、LangGraph、Celery、Redis、Pydantic、SQLAlchemy、Alembic、PostgreSQL、pgvector、S3-compatible 对象存储、Tavily、Playwright、OpenAI-compatible LLM 和 LangSmith tracing 的后端骨架。
- 文档化本地环境启动方式，同时避免引入应用 Dockerfile。

**非目标：**

- 不实现创建研究任务、运行 Agent、渲染推荐结果或生成报告等 P0 产品流程。
- 不构建超出 root directory 和启动命令约定之外的生产部署配置。
- 不加入认证、支付、团队协作或 MVP roadmap 之外的功能。
- 在出现真实共享代码之前，不引入 shared package monorepo 结构。

## 技术决策

### 使用 `frontend/` 和 `backend/`，而不是 `apps/web` 和 `apps/api`

仓库当前只有一个前端应用和一个后端应用。顶层 `frontend/` 和 `backend/` 对 MVP 更直观，也直接对应 Vercel 和 Railway 的 root-directory 设置。

备选方案是 `apps/web` 和 `apps/api`。这个结构更适合有多个 deployable apps 和 shared packages 的大型 monorepo，但对当前阶段会增加不必要的间接层。

### 将 `infra/` 保留在仓库根目录

`infra/` 描述的是整个项目的本地依赖服务，不是后端应用源码。放在根目录可以让本地运行契约更清楚，也避免 Railway 的 backend root 混入 Docker Compose 语义。

备选方案是 `backend/infra`。它短期看起来合理，因为后端会消费这些服务，但会模糊应用代码和本地依赖服务之间的边界。

### 应用进程运行在宿主机，只将依赖服务放入 Docker

本地开发运行 Next.js、FastAPI、Celery 和 LangGraph 相关进程时使用宿主机环境。Docker Compose 只提供 PostgreSQL + pgvector、Redis 和 MinIO。这与 `docs/techstack.md` 一致，也能保持线上平台源码部署的思路。

备选方案是用 Docker Compose 承载所有本地服务，包括前端和后端。这个方式适合完全容器化团队，但与当前技术栈约定不一致，也会引入暂时不需要的 Dockerfile。

### 使用 Next.js `src/app` 和本地 feature 边界

前端骨架使用 `frontend/src/app` 作为 App Router 路由目录，项目配置文件保留在 `frontend/` 根目录；复用代码放在 `frontend/src/components`、`frontend/src/hooks` 和 `frontend/src/lib`；产品相关代码从 `frontend/src/features/research`、`frontend/src/features/opportunities` 和 `frontend/src/features/reports` 开始。

Context7 查询到的 Next.js 文档说明：使用 `src` 时，特殊的 app 目录应移动到 `src/app`，而 `package.json`、`next.config`、`tsconfig`、`public` 和 `.env.*` 仍保留在应用根目录；Tailwind content path 和 TypeScript alias 需要覆盖 `src` 前缀。

备选方案是在 `frontend/` 下直接使用根级 `app/`。这也是有效结构，但 `src/app` 更利于把应用源码和配置文件分开。

### 将 shadcn/ui 作为本地源码，而不是单独 package

前端将 shadcn/ui 生成组件放在 `frontend/src/components/ui`，工具函数放在 `frontend/src/lib/utils`，配置放在 `frontend/components.json`。alias 指向本地的 `@/components`、`@/components/ui`、`@/lib`、`@/lib/utils` 和 `@/hooks`。

Context7 查询到的 shadcn/ui 文档说明：`components.json` 是项目级配置，覆盖 TypeScript、RSC、Tailwind CSS 路径、CSS variables、aliases 和 `lucide` icon library。

备选方案是提前引入 `packages/ui`。这个结构在未来有多个前端时有价值，但对 MVP 来说太早。

### 将 FastAPI 组织为包含 API、core、integrations、agents、workers 和业务模块的 package

后端骨架使用 `backend/app/main.py` 作为 ASGI 入口，并从 `backend/app/api/v1` 注册 API routers。共享配置、日志和 settings 放在 `backend/app/core`；数据库连接和迁移相关代码放在 `backend/app/db`；外部系统封装放在 `backend/app/integrations`；LangGraph 编排放在 `backend/app/agents`；Celery 入口放在 `backend/app/workers`；业务模块放在 `backend/app/modules`。

Context7 查询到的 FastAPI larger applications 文档推荐使用 `app` package、`main.py`、routers、dependencies 和模块化 `APIRouter` 注册方式。这里在该模式上增加 MarketPilot 需要的 Agent 和异步 worker 边界。

备选方案是只使用全局 `models/`、`schemas/`、`services/` 和 `repositories/` 目录。这个方式适合更小的 API，但 MarketPilot roadmap 会更自然地按 research task、opportunity、source 和 report 领域演进。

### 在 bootstrap 阶段使用 npm 和 pip 作为依赖工作流

前端 bootstrap 阶段使用 npm 脚本和 lockfile，降低新仓库启动门槛，也能直接匹配 Next.js 官方 `create-next-app` 路径。后端 bootstrap 阶段使用标准 Python virtualenv + pip，并用 `pyproject.toml` 管理项目元数据、依赖和测试工具。

备选方案是 pnpm、bun、poetry 或 uv。这些工具都有价值，但当前技术栈未指定它们；先用默认工具可以减少项目骨架阶段的工具决策成本，后续需要时再通过独立 change 迁移。

## 风险 / 取舍

- [Risk] 骨架可能比第一个 P0 切片需要的内容更多 -> Mitigation: 只创建最小占位文件，不在 bootstrap 阶段实现产品行为。
- [Risk] 依赖版本可能在 proposal 和 implementation 之间变化 -> Mitigation: apply 阶段使用当前包管理器解析结果并提交 lockfile。
- [Risk] 前后端 API 契约后续可能分叉 -> Mitigation: 现在先文档化 API base URL 约定，等第一个真实接口出现后再考虑 OpenAPI client generation。
- [Risk] Railway web 和 worker 的启动命令可能逐渐分化 -> Mitigation: 从一开始就把后端进程命令文档化，并保持环境变量驱动。
- [Risk] 本地 MinIO 与 Railway Storage Buckets 不完全一致 -> Mitigation: 对象存储访问统一收敛到 S3-compatible integration module。

## 迁移计划

1. 新增 scaffold 目录和基础配置文件。
2. 新增 frontend、backend 和 infra 的环境变量示例。
3. 在根目录 `infra/` 下新增本地依赖服务 Compose 配置。
4. 更新 README，说明依赖安装、本地服务启动、前端启动、后端 API 启动、Celery worker 启动和骨架验证方式。
5. 分别验证前端和后端 baseline checks。

如果需要回滚，因为当前还没有生产数据或既有应用行为，删除新增骨架目录并还原 README 变更即可。

## 开放问题

- API client generation 应该在第一个真实后端接口出现后立即引入，还是等 API 面扩大后再引入？
