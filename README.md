# Fox MarketPilot

MarketPilot 是面向国内中文演示场景的商机顾问 Agent。

## 仓库结构

```text
frontend/   Next.js + TypeScript 前端应用
backend/    FastAPI + Celery + Agent 后端应用
infra/      本地依赖服务：PostgreSQL + pgvector、Redis、MinIO
docs/       产品和技术文档
openspec/   OpenSpec changes 和长期规格
```

## 应用入口

- 前端说明见 [frontend/README.md](frontend/README.md)。
- 后端说明见 [backend/README.md](backend/README.md)。

## 一键运行

```bash
scripts/startup.sh
scripts/shutdown.sh
```

## 本地依赖

本地依赖服务说明见 [infra/README.md](infra/README.md)。
