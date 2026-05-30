## Why

当前 P0 已能生成基础商机推荐、详情和基础报告，但这些判断仍明确标识为“待验证草案”，没有可追溯的公开来源线索。为了提升用户信任并为后续需求洞察、货源候选、竞品参考和风险分析打地基，需要先把研究来源收集、摘要、关联和读取能力落到稳定契约中。

## What Changes

- 为每次成功的商机研究运行收集公开来源线索，保存来源标题、链接、摘要、片段、来源类型和关联判断。
- 允许来源关联到研究任务，并可选关联到单个商机，支撑后续按商机或报告章节展示来源。
- 在基础研究 LangGraph 流程中新增来源收集阶段，并记录阶段事件、状态和失败摘要。
- 提供读取任务来源与商机来源的后端 API；前端展示留给 `show-source-transparency`，本 change 只要求 API 可被后续视图使用。
- 保持谨慎语气：来源表示“公开线索”或“初步参考”，不宣称商机已被证明、供给已确认或竞品已全面核验。
- 来源收集失败或外部搜索凭证缺失时，不破坏既有 P0 商机结果闭环；系统应保留基础推荐并给出可排障的来源收集状态。

## Capabilities

### New Capabilities

- `research-sources`: 定义研究来源的收集、持久化、关联、读取、失败降级和谨慎表达契约。

### Modified Capabilities

- `opportunity-research`: 基础研究运行成功保存商机后，新增可观测的来源收集阶段；该阶段不改变基础商机生成 schema。
- `research-progress`: 任务进度页可以识别来源收集阶段及其完成、跳过或失败状态。
- `agent-run-observability`: Agent 阶段事件覆盖来源收集阶段，便于查看搜索、提取和摘要相关失败。

## Impact

- Backend: 新增 `sources` 领域模型、schema、repository、service、API 路由和 Alembic migration。
- Agent runtime: 在现有 LangGraph 单图中增加来源收集节点；本 change 不引入多 Agent 编排。
- Integrations: 使用 Tavily Search 收集公开结果，必要时使用 Tavily Extract 获取正文；本地或测试环境可使用确定性 fallback，自动化测试不依赖外部网络。
- Database: 新增研究来源表，关联 `research_tasks` 与可选 `opportunities`。
- API: 新增任务来源列表和商机来源列表读取接口。
- Observability: 来源收集阶段写入 `agent_run_events`，并保留任务当前阶段展示所需状态。
- Out of scope: 来源透明度 UI、完整 RAG、向量检索、来源引用评测、多 Agent 分析、深度竞品/供给/风险结论生成。
