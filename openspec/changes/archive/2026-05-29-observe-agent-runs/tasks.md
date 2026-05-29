## 1. LangSmith 配置与观测工具

- [x] 1.1 将现有 LangSmith 环境配置接入 FastAPI 和 Celery worker 启动路径，确保 API 与后台 worker 都能读取 `LANGSMITH_TRACING`、`LANGSMITH_API_KEY` 和 `LANGSMITH_PROJECT`。
- [x] 1.2 增加 Agent run observability 辅助模块，统一处理 root run metadata、stage start/complete/fail 日志、耗时计算和 tracing disabled no-op 行为。
- [x] 1.3 为 OpenAI-compatible LLM client 增加 LangSmith tracing 包装或 traceable 边界，并确保 metadata 包含 provider、model、task UUID 和 run ID。
- [x] 1.4 确认 trace metadata、日志 extra 和用户可见失败原因不写入 API key、原始堆栈或内部自增 ID。
- [x] 1.5 增加可选 LangSmith trace URL 构造或保存能力；无法可靠构造 URL 时保持为空，不影响任务读取。
- [x] 1.6 文档化推荐的 LangSmith project 命名：`marketpilot-dev` 和 `marketpilot-prod`，并保持 `LANGSMITH_PROJECT` 可配置。

## 2. 阶段历史持久化

- [x] 2.1 新增 `agent_run_events` SQLAlchemy model 和 Alembic migration，包含内部自增 ID、公开 UUID、时间戳、软删除字段、任务关联、run ID、trace ID、阶段、状态、开始时间、完成时间、耗时、错误摘要和 metadata。
- [x] 2.2 增加 `agent_run_events` repository/service，默认只读取 `deleted_at` 为空的事件，并按运行和阶段时间稳定排序。
- [x] 2.3 在阶段开始、阶段完成和阶段失败时写入或更新运行事件，确保成功和失败运行都能保留完整历史。
- [x] 2.4 重新运行任务时保留旧运行事件，并通过新的 run ID 保存新一轮阶段历史。

## 3. 研究任务运行链路

- [x] 3.1 在启动新研究运行时生成新的 `run_id`，清空上一轮 `failure_reason`，并清理或刷新上一轮 `trace_id`。
- [x] 3.2 在研究运行入口建立 `opportunity_research` root trace，LangSmith tracing 启用时读取并回写任务 `trace_id`。
- [x] 3.3 在 LangGraph 主要节点 `normalize_intake`、`generate_opportunities`、`validate_results` 和 `persist_results` 周围记录阶段开始、完成和耗时。
- [x] 3.4 扩展后端 `ResearchTaskStage` 与前端阶段 label，使任务列表能识别更细的运行阶段。
- [x] 3.5 在 Agent 执行、LLM 调用、结果解析、校验或持久化失败时记录失败阶段，并保存中文可理解失败摘要。
- [x] 3.6 确认可观测系统异常只记录 warning，不让研究任务仅因 LangSmith 初始化或 trace id 获取失败而失败。

## 4. API 与前端兼容

- [x] 4.1 保持现有研究任务 API 响应结构不破坏，继续返回 `run_id`、`trace_id`、`failure_reason` 和公开任务 UUID。
- [x] 4.2 更新前端研究任务类型与阶段文案，确保更细阶段、失败状态和 tracing disabled 场景都有中文可读展示。
- [x] 4.3 在 `/research/tasks` 任务列表操作区增加可选 LangSmith 外链入口；仅当任务存在 trace URL 时展示，点击后新标签打开。
- [x] 4.4 不新增完整进度页或 SSE；只保证现有任务列表/任务读取入口可以承载新阶段、trace 关联字段和 LangSmith 外链。

## 5. 自动化测试

- [x] 5.1 增加 tracing disabled 测试：未配置 LangSmith env 时研究运行仍成功，`trace_id` 可以为空。
- [x] 5.2 增加 trace id 回写测试：使用 fake tracing context 或可注入 observer 验证任务记录保存当前运行 trace ID。
- [x] 5.3 增加阶段事件落库测试：成功运行后保存每个主要阶段的状态、开始时间、完成时间和耗时。
- [x] 5.4 增加节点失败测试：模拟生成、校验或持久化失败，验证任务状态、失败摘要、失败阶段日志和失败事件记录。
- [x] 5.5 增加重新运行测试：验证新运行刷新 `run_id`，清空旧失败原因，替换或清空旧 `trace_id`，并保留旧运行事件。
- [x] 5.6 增加日志上下文测试或断言，验证运行开始、阶段完成和失败日志包含 task UUID、run ID、trace ID、stage 和 duration。
- [x] 5.7 增加前端或类型测试，验证有 trace URL 的任务展示 LangSmith 外链，没有 trace URL 的任务不展示入口。

## 6. 验证与交付

- [x] 6.1 运行 backend 测试与 lint，确认不需要真实 LangSmith、DeepSeek 或外部网络凭证。
- [x] 6.2 本地无 LangSmith env 启动 API 和 worker，创建并执行一次研究任务，确认基础闭环无回归且阶段事件已落库。
- [x] 6.3 实现完成后提醒用户把 LangSmith env 写入 backend 实际启动环境，不在仓库中提交真实 API key。
- [x] 6.4 用户写入 LangSmith env 后，执行一次真实研究任务，确认 LangSmith 项目中能看到 root run、节点 run、LLM run 和任务 trace ID 关联。
- [x] 6.5 用户写入 LangSmith env 后，从任务列表点击 LangSmith 外链，确认能打开对应 trace 页面并查看运行树、错误、耗时和 token 等指标。
- [x] 6.6 更新必要 README 或 `.env.example` 说明，明确 tracing env、推荐 project 命名、worker 环境一致性、外链权限和关闭 tracing 的回滚方式。
