## 1. 数据模型与迁移

- [x] 1.1 新增 `ResearchSource` SQLAlchemy model，包含内部 `id`、公开 `uuid`、`created_at`、`updated_at`、`deleted_at`、任务关联、可选商机关联和来源业务字段。
- [x] 1.2 新增 Alembic migration 创建 `research_sources` 表、索引和外键，并保证默认读取可按任务、商机、来源类型和软删除状态过滤。
- [x] 1.3 新增来源 Pydantic schema，覆盖 `source_type`、`support_level`、公开读取响应和内部生成输入。
- [x] 1.4 新增 sources repository/service，支持创建来源、按任务列出来源、按商机列出来源、软删除旧来源和同任务 URL 去重。

## 2. 来源收集核心逻辑

- [x] 2.1 实现来源 query builder，根据研究任务输入、商机名称、产品方向、目标人群、渠道和供给偏好生成受控 query。
- [x] 2.2 实现 Tavily search 适配层，读取标题、URL、片段、score 和 raw metadata，并支持测试替身注入。
- [x] 2.3 实现可选 Tavily Extract 增强逻辑，对少量高分 URL 提取正文，提取失败时回退到搜索片段。
- [x] 2.4 实现来源摘要与关联判断生成，输出中文谨慎语气的 `summary`、`linked_claim` 和 `support_level`。
- [x] 2.5 实现 local/test 环境无搜索凭证时的确定性 fallback 或跳过策略，确保自动化测试不依赖外部网络。
- [x] 2.6 实现单任务来源数量上限、query 数量上限和同任务 URL 去重。

## 3. LangGraph 运行接入

- [x] 3.1 在后端研究任务阶段枚举中加入 `collect_research_sources`，并补齐前端 API 类型和中文阶段标签。
- [x] 3.2 在现有 LangGraph 单图中于 `persist_results` 后新增 `collect_research_sources` 节点。
- [x] 3.3 来源收集节点成功时保存来源并将任务推进到 `completed`。
- [x] 3.4 来源收集全部失败、部分失败或跳过时保留已生成商机结果，并记录安全失败摘要或 metadata。
- [x] 3.5 重新运行成功时软删除或默认排除旧来源，确保来源列表只展示当前运行结果。

## 4. API 与进度展示

- [x] 4.1 新增 `GET /api/v1/research-tasks/{task_uuid}/sources`，返回任务未软删除来源列表。
- [x] 4.2 新增 `GET /api/v1/opportunities/{opportunity_uuid}/sources`，返回单个商机关联来源列表。
- [x] 4.3 确保来源 API 不暴露内部自增 ID，并对不存在或已软删除任务/商机返回未找到错误。
- [x] 4.4 更新研究进度 API 和前端进度时间线，使 `collect_research_sources` 以“收集公开来源线索”的中文文案展示。
- [x] 4.5 保持商机列表、商机详情和基础报告现有入口可用，不在本 change 实现完整来源透明度 UI。

## 5. 可观测性与安全

- [x] 5.1 为来源收集阶段写入 `agent_run_events`，包含阶段名称、状态、耗时、run ID 和可空 trace ID。
- [x] 5.2 为来源收集记录应用日志，包含任务 UUID、运行 ID、query 数量、保存来源数量和结果状态。
- [x] 5.3 LangSmith tracing 启用时，将来源收集阶段关联到同一条研究运行 trace。
- [x] 5.4 确保用户可见失败摘要不包含 API key、原始堆栈、完整请求头或内部自增 ID。

## 6. 测试与验证

- [x] 6.1 添加 sources repository/service/API 测试，覆盖保存、读取、软删除过滤、URL 去重和不存在资源错误。
- [x] 6.2 添加来源收集器测试，覆盖 Tavily search mocked response、extract fallback、local/test deterministic fallback 和谨慎语气输出。
- [x] 6.3 添加研究运行集成测试，覆盖成功保存来源、来源全部失败不阻塞任务完成、部分成功保留可用来源和重新运行替换旧来源。
- [x] 6.4 添加进度和可观测性测试，确认 `collect_research_sources` 阶段事件、进度响应和安全错误摘要符合规格。
- [x] 6.5 运行后端测试、前端 lint/type check，并确认不需要真实 Tavily、DeepSeek 或 LangSmith 凭证即可通过自动化测试。
- [x] 6.6 手动演示一次本地研究任务，确认完成后商机结果可读取、来源 API 可读取，且来源收集失败不会破坏 P0 闭环。
