## 1. 后端数据与 API

- [x] 1.1 新增 Alembic 迁移，创建 `validation_budgets` 表，包含内部 `id`、公开 `uuid`、`research_task_id`、`opportunity_id`、估算字段、`estimate_status`、时间戳和软删除字段。
- [x] 1.2 新增 `validation_budgets` 后端模块，包含 SQLAlchemy model、Pydantic schema、repository 和基础读取转换函数。
- [x] 1.3 实现验证预算服务，支持按任务替换当前预算估算、按任务读取、按商机读取、默认排除软删除记录。
- [x] 1.4 实现验证预算生成器，支持 LLM 结构化输出、Pydantic 校验、谨慎文案校验、一次重试和 local/test 确定性 fallback。
- [x] 1.5 新增验证预算 API 路由，提供按研究任务读取和按商机读取接口，并确保响应不暴露内部自增 ID。

## 2. Agent 流程与可观测性

- [x] 2.1 在研究任务阶段枚举、失败阶段映射和前端共享类型中加入 `estimate_validation_budgets`。
- [x] 2.2 在 LangGraph 中把验证预算估算节点接到 `generate_competitor_references` 之后，并保持失败非阻塞。
- [x] 2.3 在验证预算阶段记录 Agent run event metadata，包括估算状态、保存数量和失败摘要。
- [x] 2.4 在 LLM 调用 metadata 中加入 provider、model、任务 UUID 和 run ID，并避免写入敏感凭证或精确财务承诺。

## 3. 前端展示

- [x] 3.1 在前端 API client 中新增验证预算类型、任务级读取函数和商机级读取函数。
- [x] 3.2 新增验证预算展示组件，覆盖加载、失败、空结果、完整预算卡片和谨慎中文文案。
- [x] 3.3 将商机详情页接入完整验证预算估算，展示成本、售价、毛利、首批数量、首批预算、关键假设和估算说明。
- [x] 3.4 将基础报告页接入任务级验证预算摘要，展示每个商机的首批预算和至少一个关键假设。
- [x] 3.5 更新研究进度页阶段文案和时间线，让 `estimate_validation_budgets` 显示为用户可理解的验证预算估算阶段。

## 4. 测试与验证

- [x] 4.1 增加后端测试，覆盖验证预算生成、读取、fallback、谨慎文案校验、内部 ID 不暴露和空结果。
- [x] 4.2 增加重新运行测试，确认旧验证预算被软删除或从默认读取中排除，新预算关联当前商机。
- [x] 4.3 增加研究运行测试，确认阶段链路包含 `estimate_validation_budgets`，且该阶段失败不破坏基础结果。
- [x] 4.4 增加前端 UI 契约测试，确认商机详情、基础报告和进度页包含验证预算展示与非阻塞状态。
- [x] 4.5 运行后端测试、前端测试和 `openspec validate estimate-validation-budget --strict`。
- [x] 4.6 本地完成一次中文示例研究演示验证，确认商机详情和基础报告可看到验证预算估算，缺少预算时页面仍可阅读。
