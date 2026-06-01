## 1. 数据模型和模块骨架

- [x] 1.1 新增 `research_quality_readiness_runs` Alembic migration，包含内部 `id`、公开 `uuid`、`research_task_id`、`research_run_id`、状态字段、检查明细 JSON、汇总指标 JSON、可空 RAG 评测 run UUID、trace 字段、时间字段和软删除字段。
- [x] 1.2 建立 `backend/app/modules/research_quality_readiness/` 模块，包含 models、schemas、repository、service 和 runner 入口。
- [x] 1.3 在数据库 base metadata、API router 和测试 fixture 中接入新模块，确保 active 读取默认排除 `deleted_at` 非空记录。

## 2. 后端 readiness 检查服务

- [x] 2.1 实现 readiness run 创建、最近结果读取、过期判断和安全响应转换，不暴露内部自增 ID。
- [x] 2.2 实现阶段完整性检查，覆盖基础推荐、结果保存、来源收集、RAG 索引、需求洞察、货源候选、竞品参考、验证预算、风险复核和行动计划阶段。
- [x] 2.3 实现 RAG 索引健康检查，统计 active 来源数、active chunk 数、embedding 状态、fallback/skipped/failed 原因和任务内检索可用性。
- [x] 2.4 集成现有 RAG 检索评测服务，保存评测 run 公开 UUID、case 状态和 P0 指标摘要，并在失败时降级为 readiness warning 或 failed。
- [x] 2.5 实现生成内容 smoke check，检查商机和增强分析字段完整性、数量不足、空内容和谨慎边界文案。
- [x] 2.6 实现整体状态聚合规则，将检查项状态汇总为 `ready`、`warning` 或 `failed`。
- [x] 2.7 为 readiness 检查记录结构化日志和可选 LangSmith trace metadata，避免写入 API key、完整正文、chunk 原文或内部自增 ID。

## 3. 内部 API 和命令入口

- [x] 3.1 新增创建 readiness run 的内部 API，例如 `POST /api/v1/research-tasks/{task_uuid}/readiness-runs`。
- [x] 3.2 新增读取最近 readiness run 的内部 API，例如 `GET /api/v1/research-tasks/{task_uuid}/readiness-runs/latest`。
- [x] 3.3 新增内部 runner 命令，可对指定任务 UUID 运行 readiness 检查并导出安全 JSON 摘要。
- [x] 3.4 确保未完成任务、任务不存在、RAG 评测失败和检查异常都有中文安全错误摘要，且不修改研究任务状态。

## 4. 前端展示

- [x] 4.1 在 `frontend/src/features/research/api.ts` 增加 readiness run 类型、创建函数和最近结果读取函数。
- [x] 4.2 在研究任务进度页新增「演示就绪检查」面板，展示未检查、检查中、可演示、需复查、失败和已过期状态。
- [x] 4.3 在进度页面板中提供运行检查入口，并在完成后刷新最新 readiness 结果。
- [x] 4.4 在研究历史列表为已完成任务增加轻量 readiness badge，避免展示 RAG chunk、完整评测明细、trace metadata 或内部 ID。
- [x] 4.5 确认公开分享页不调用 readiness API，也不展示 readiness、RAG 评测、trace 或内部错误信息。

## 5. 测试和验证

- [x] 5.1 增加后端测试覆盖 readiness run 创建、最近结果读取、过期判断、未完成任务拒绝和安全响应字段。
- [x] 5.2 增加后端测试覆盖阶段完整性、RAG 索引健康、RAG 检索评测降级和生成内容 smoke check。
- [x] 5.3 增加后端测试确认 readiness 检查失败不修改研究任务状态、不删除商机、来源、RAG chunks、增强分析、评测结果或分享记录。
- [x] 5.4 增加前端契约测试，确认进度页展示 readiness 面板、历史页展示轻量 badge、公开分享页不展示内部质量检查。
- [x] 5.5 运行 `openspec validate add-research-quality-readiness --strict`，并运行相关后端和前端测试。
