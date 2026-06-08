## 为什么

当前研究运行已经具备来源收集、任务内 RAG 证据索引、需求洞察、货源候选、竞品参考、验证预算、风险复核和行动计划等完整增强分析链路，但这些阶段在 LangGraph 中按固定线性顺序执行。需求洞察、货源候选和竞品参考本质上是同一批基础商机与来源证据上的独立分析分支，继续串行会增加端到端等待时间，也弱化了“多个专业分析视角协作后汇总”的 Agent 运行表达。

本 change 将研究分析中可独立执行的专业分析阶段调整为并行 fan-out，并在预算、风险和行动计划前增加汇总边界，让系统更接近轻量 multi-agent 工作流，同时保持现有 MVP 结果、来源谨慎表达和失败不阻断基础结果的边界。

## 变更内容

- 将 `generate_demand_insights`、`generate_supply_candidates` 和 `generate_competitor_references` 从严格串行阶段调整为可并行执行的 specialist analysis branches。
- 增加研究分析汇总边界，等待需求、货源和竞品分支完成、跳过或安全失败后，再进入验证预算估算、风险复核和行动计划。
- 保持基础商机生成、来源收集和任务内 RAG 证据索引仍在并行分析之前完成；不在生成基础推荐前做外部前置调研。
- 保持增强分析失败不覆盖基础商机结果：任一并行分支失败时记录安全阶段事件，其他分支和后续可用阶段仍可继续。
- 更新 Agent run observability，使阶段事件、LangSmith trace metadata 和应用日志能够表达并行分支的开始、完成、失败和汇总结果。
- 更新研究进度展示契约，使用户能看到多个专业分析阶段同时运行或已分别完成，而不是只看到单一线性当前阶段。
- 不新增用户输入字段、不新增公开结果 API 能力、不引入新的 multi-agent 框架或外部服务依赖。

## 能力

### 新增能力

无。

### 修改能力

- `opportunity-research`: 研究运行从线性增强分析链路调整为来源和 RAG 之后并行执行需求洞察、货源候选和竞品参考，并在汇总后继续预算、风险和行动计划。
- `agent-run-observability`: Agent 阶段历史和 trace 需要支持并行专业分析分支、汇总阶段和分支级失败 metadata。
- `research-progress`: 研究进度页需要展示并行分析阶段的多个运行中或已完成状态，并在汇总完成后继续展示后续串行阶段。

## 影响

- Affected backend: `backend/app/agents/graph.py`、`backend/app/modules/research_tasks` 阶段枚举与进度 schema、`backend/app/modules/agent_runs` 阶段事件读写、相关测试。
- Affected frontend: 研究进度页阶段时间线、阶段文案和运行中刷新展示。
- Affected observability: LangSmith trace、应用日志和 `agent_run_events` metadata 需要能区分并行分支和汇总结果。
- Affected specs: `opportunity-research`、`agent-run-observability`、`research-progress`。
- Dependencies: 继续使用现有 LangGraph、Celery、SQLAlchemy、LangSmith 和 OpenAI-compatible provider；不新增外部服务或数据库表作为必选范围。
