# MarketPilot Infra

这里放本地开发依赖服务配置。应用进程不在 Docker Compose 中运行。

## 服务

```text
PostgreSQL + pgvector   localhost:5432
Redis                   localhost:6379
MinIO API               localhost:9000
MinIO Console           localhost:9001
```

## 常用命令

```bash
cp infra/.env.example infra/.env
docker compose --env-file infra/.env -f infra/compose.yaml up -d
docker compose --env-file infra/.env -f infra/compose.yaml config
docker compose --env-file infra/.env -f infra/compose.yaml down
```
