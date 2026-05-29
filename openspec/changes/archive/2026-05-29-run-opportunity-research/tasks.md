## 1. 数据模型与迁移

- [x] 1.1 扩展 `ResearchTaskStatus` 和 `ResearchTaskStage`，支持 `queued`、`running`、`completed`、`failed` 以及本 change 需要的执行阶段。
- [x] 1.2 新增 `Opportunity` SQLAlchemy model，包含内部自增 `id`、公开 `uuid`、`research_task_id`、排序、P0 商机字段、`created_at`、`updated_at` 和可空 `deleted_at`。
- [x] 1.3 新增 Alembic migration 创建 `opportunities` 表，包含任务外键、商机 UUID 唯一约束、任务排序唯一约束或等效保护，以及 `deleted_at`/任务排序相关索引。
- [x] 1.4 确保软删除读取约定一致：默认列表和详情查询只返回 `deleted_at IS NULL` 的商机结果。

## 2. 商机结果领域能力

- [x] 2.1 在 `backend/app/modules/opportunities` 下新增 Pydantic schemas，覆盖商机创建、读取、列表和 LLM 结构化输出校验。
- [x] 2.2 新增 opportunities repository，支持按任务列出商机、按 UUID 读取商机、批量保存新商机和软删除任务旧商机。
- [x] 2.3 新增 opportunities service，封装排序校验、字段校验、重新运行替换旧结果和对外读取契约。
- [x] 2.4 新增 API routes：`GET /api/v1/research-tasks/{task_uuid}/opportunities` 和 `GET /api/v1/opportunities/{opportunity_uuid}`。

## 3. 研究运行与 Agent

- [x] 3.1 新增 research run service，支持 `POST /api/v1/research-tasks/{task_uuid}/runs` 启动研究运行。
- [x] 3.2 启动运行时校验任务存在且未软删除，生成 `run_id`，设置 `queued` 状态，清空失败原因，并避免对 `queued`/`running` 任务重复投递。
- [x] 3.3 新增 Celery 研究任务，执行开始时设置 `running/generate_opportunities`，完成时设置 `completed/completed`，失败时设置 `failed/failed` 和中文失败原因。
- [x] 3.4 在 `backend/app/agents/graph.py` 中实现 LangGraph 单图工作流：`normalize_intake`、`generate_opportunities`、`validate_results`、`persist_results`。
- [x] 3.5 让 Celery 研究任务装载研究任务上下文并调用 LangGraph 图执行，节点完成后回写任务状态和商机结果。
- [x] 3.6 实现 OpenAI-compatible LLM 生成器，基于研究任务输入、表单条件和默认产品场景直接生成 3-5 个结构化中文商机结果，并对无效输出执行一次可控重试或失败处理。
- [x] 3.7 实现 deterministic fallback generator，在 local/test 且缺少 `LLM_API_KEY` 时稳定生成 3 个符合 schema 的中文商机。
- [x] 3.8 为 LangGraph 运行记录基础应用日志，至少包含任务 UUID、运行 ID、节点/阶段、结果状态和失败摘要，不记录敏感凭证。
- [x] 3.9 确认本 change 的研究运行不调用 Tavily、Playwright、网页提取、RAG、pgvector 检索或来源收集模块。

## 4. 前端真实结果接入

- [x] 4.1 扩展前端 research task 类型和状态文案，支持 `created`、`queued`、`running`、`completed`、`failed`。
- [x] 4.2 新增前端 API client 方法，用于启动研究运行、读取某任务商机列表和读取单个商机详情。
- [x] 4.3 更新新建研究成功后的流程：自动启动基础研究运行，并回到任务列表或任务入口展示运行状态。
- [x] 4.4 更新研究任务列表操作入口，根据状态展示“开始研究”“查看商机”或“重新运行”等中文操作。
- [x] 4.5 更新商机推荐页，从真实任务商机 API 读取数据；任务未完成或无结果时展示中文状态说明，不把静态 demo 商机当作真实结果。
- [x] 4.6 更新商机详情页，通过商机 UUID 读取真实详情，并展示关联任务入口。
- [x] 4.7 更新基础报告入口，使其能基于任务商机结果展示推荐排序、商机摘要、风险等级和下一步行动摘要。
- [x] 4.8 调整结果相关中文文案，将输出表达为基础推荐、待验证商机或验证草案，避免暗示已完成公开调研、来源引用或竞品核验。

## 5. 测试与验证

- [x] 5.1 新增后端测试覆盖启动研究运行、重复启动运行中任务、读取不存在或软删除任务、成功状态迁移和失败状态迁移。
- [x] 5.2 新增后端测试覆盖商机结果保存、排序、列表读取、详情读取、软删除过滤和重新运行替换旧结果。
- [x] 5.3 新增后端测试覆盖 LangGraph 节点执行、LLM 输出校验失败、fallback 生成和无外部 LLM 凭证的测试路径。
- [x] 5.4 新增或更新前端测试/类型检查，覆盖任务状态文案、启动运行 API、真实商机列表和详情读取路径。
- [x] 5.5 新增测试或代码检查，确认基础研究运行不会调用外部前置调研工具或创建来源记录。
- [x] 5.6 运行后端 `pytest` 和 `ruff check .`，确认新后端能力通过。
- [x] 5.7 运行前端 `npm run lint`、`npm run typecheck` 和必要的构建检查，确认真实结果页面类型正确。
- [x] 5.8 使用本地启动流程验证一条中文示例需求可以创建任务、启动研究、生成至少 3 个商机，并从排行榜进入详情和基础报告视图。

## 6. 文档与收尾

- [x] 6.1 更新相关 README 或环境变量说明，解释 local/test 缺少 `LLM_API_KEY` 时会使用确定性 fallback，生产环境应配置真实 LLM 凭证。
- [x] 6.2 确认 `openspec validate run-opportunity-research --strict` 通过。
- [x] 6.3 确认本 change 使用 LangGraph 单图工作流，但没有实现多 Agent、外部前置调研、来源收集、RAG、竞品深挖、完整报告模型或 LangSmith 完整 tracing。
