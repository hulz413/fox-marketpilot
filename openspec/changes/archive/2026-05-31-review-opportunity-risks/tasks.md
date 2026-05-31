## 1. 后端数据与 API

- [x] 1.1 新增 Alembic 迁移，创建 `opportunity_risks` 表，包含内部 `id`、公开 `uuid`、`research_task_id`、`opportunity_id`、风险字段、`review_status`、时间戳和软删除字段。
- [x] 1.2 新增 `opportunity_risks` 后端模块，包含 SQLAlchemy model、Pydantic schema、repository 和基础读取转换函数。
- [x] 1.3 实现风险复核服务，支持按任务替换当前风险复核、按任务读取、按商机读取、默认排除软删除记录。
- [x] 1.4 实现风险复核生成器，支持 LLM 结构化输出、Pydantic 校验、谨慎文案校验、一次重试和 local/test 确定性 fallback。
- [x] 1.5 新增风险复核 API 路由，提供按研究任务读取和按商机读取接口，并确保响应不暴露内部自增 ID。

## 2. Agent 流程与可观测性

- [x] 2.1 在研究任务阶段枚举、失败阶段映射和前端共享类型中加入 `review_opportunity_risks`。
- [x] 2.2 在 LangGraph 中把风险复核节点接到 `estimate_validation_budgets` 之后，并保持失败非阻塞。
- [x] 2.3 在风险复核阶段记录 Agent run event metadata，包括复核状态、保存数量和失败摘要。
- [x] 2.4 在 LLM 调用 metadata 中加入 provider、model、任务 UUID 和 run ID，并避免写入敏感凭证、正式合规结论或供应链尽调结论。

## 3. 前端展示

- [x] 3.1 在前端 API client 中新增风险复核类型、任务级读取函数和商机级读取函数。
- [x] 3.2 新增风险复核展示组件，覆盖加载、失败、空结果、完整风险卡片和谨慎中文文案。
- [x] 3.3 将商机详情页接入完整风险复核，展示综合风险等级、风险摘要、分项风险、触发原因和缓解建议。
- [x] 3.4 将基础报告页接入任务级风险摘要，展示每个商机的风险等级、风险摘要和至少一个优先排查点。
- [x] 3.5 更新研究进度页阶段文案和时间线，让 `review_opportunity_risks` 显示为用户可理解的风险复核阶段。

## 4. 测试与验证

- [x] 4.1 增加后端测试，覆盖风险复核生成、读取、fallback、谨慎文案校验、内部 ID 不暴露和空结果。
- [x] 4.2 增加重新运行测试，确认旧风险复核被软删除或从默认读取中排除，新风险复核关联当前商机。
- [x] 4.3 增加研究运行测试，确认阶段链路包含 `review_opportunity_risks`，且该阶段失败不破坏基础结果。
- [x] 4.4 增加前端 UI 契约测试，确认商机详情、基础报告和进度页包含风险复核展示与非阻塞状态。
- [x] 4.5 更新 `docs/mvp/roadmap.md` 中 `review-opportunity-risks` 的进度说明和当前闭环描述。
- [x] 4.6 运行后端测试、前端测试和 `openspec validate review-opportunity-risks --strict`。
- [x] 4.7 本地完成一次中文示例研究演示验证，确认商机详情和基础报告可看到风险复核，缺少风险复核时页面仍可阅读。
