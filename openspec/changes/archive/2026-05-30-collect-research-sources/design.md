## 背景

MarketPilot 目前已经完成 P0 可观测闭环：用户可以创建研究任务、启动基础商机研究、查看进度、获得 3-5 个待验证商机、打开详情和基础报告。现有 `opportunity-research` 明确不做外部前置调研，UI 也以“基础推荐”“待验证草案”表达结果边界。

`collect-research-sources` 是 P1 的第一块质量增强切片。它需要在不破坏 P0 闭环的前提下，收集公开来源线索并保存为后续需求洞察、货源候选、竞品参考、风险分析和来源透明度 UI 可复用的证据层。

当前代码已有：

- `backend/app/modules/sources/` 占位目录。
- Tavily integration 占位。
- LangGraph 单图研究流程和 `agent_run_events` 阶段事件。
- `research_tasks`、`opportunities` 持久化模型与公开 UUID 读取 API。

## 目标 / 非目标

**目标：**

- 新增研究来源数据模型，保存公开来源标题、URL、摘要、片段、来源类型、关联判断和支撑强度。
- 来源可以关联到研究任务，并可选关联到单个商机。
- 在现有 LangGraph 单图中新增 `collect_research_sources` 节点，在商机持久化后运行。
- 使用 Tavily Search 收集公开结果，必要时使用 Tavily Extract 获取正文；本地和测试环境提供确定性 fallback。
- 来源收集失败、跳过或部分成功时不让已生成的 P0 商机结果变成失败任务。
- 为来源收集阶段写入 Agent run event、日志和 trace metadata，便于排障。
- 提供任务来源列表和商机来源列表 API，默认只返回未软删除来源。

**非目标：**

- 不实现来源透明度 UI；展示层由后续 `show-source-transparency` 负责。
- 不引入多 Agent 编排；本 change 只在现有单图中新增来源收集节点。
- 不实现 RAG、向量检索、评测集或引用质量评分。
- 不让来源反向改变本轮商机排序、风险等级或推荐理由。
- 不做登录后平台数据抓取、自动联系供应商、自动下单或私域数据采集。
- 不声称来源已经证明商机成立、供给已确认或竞品已全面核验。

## 技术决策

### 1. 来源收集放在商机持久化之后

新增节点顺序为：

```text
normalize_intake
  -> generate_opportunities
  -> validate_results
  -> persist_results
  -> collect_research_sources
  -> END
```

这样可以保持当前 P0 生成逻辑稳定。商机推荐仍然直接基于任务输入和默认演示场景生成；来源收集只为已经保存的商机补充公开线索。

Alternative considered: 在生成商机前先搜索公开来源，再让模型基于来源生成推荐。这个路径更接近完整研究 Agent，但会同时改变推荐质量、提示词、失败模式和用户预期，范围过大，留给后续 P1/P2 研究增强。

### 2. 单图节点，不引入多 Agent

本 change 使用一个 `SourceCollector` service 和一个 LangGraph node。节点内部可以为需求、货源、竞品和风险生成多组 query，但这些是普通子步骤，不是独立 Agent。

多 Agent 更适合在 `explain-demand-insights`、`suggest-supply-candidates`、`compare-competitor-references`、`review-opportunity-risks` 和 `create-action-plan` 组合阶段引入。那时不同角色会基于来源做独立判断，并需要合并冲突结论。

Alternative considered: 立即引入 Demand/Supply/Competitor/Risk 多 Agent。它能更贴近最终产品形态，但会增加调度、trace、失败恢复和结论合并复杂度，不适合作为来源数据层的第一步。

### 3. 来源数据模型采用任务关联 + 可选商机关联

新增 `research_sources` 表，遵循项目通用数据库字段规范：

- 内部自增 `id`。
- 公开 `uuid`。
- `created_at`、`updated_at`、`deleted_at`。
- `research_task_id` 必填，关联研究任务。
- `opportunity_id` 可空，关联单个商机。

业务字段建议包括：

- `source_type`: `demand`、`supply`、`competitor`、`risk`、`general`。
- `title`、`url`、`summary`、`snippet`。
- `publisher` 可空。
- `score` 可空。
- `query` 可空，用于排障。
- `linked_claim`，描述该来源关联的判断。
- `support_level`: `weak`、`medium`、`strong`。
- `raw_metadata` JSON，用于保存 Tavily score、extract 状态等非稳定字段。
- `collected_at`。

读取默认只返回 `deleted_at` 为空的记录。重新运行研究任务成功后，旧来源应被软删除或从默认读取中排除，并保存当前 run 的新来源。

Alternative considered: 建立独立 `claims` 表和 source-claim 多对多关系。这个模型更完整，但会把 `show-source-transparency` 和分析切片的工作提前。第一版用 `linked_claim` 字段即可满足来源线索和后续演进。

### 4. 来源查询受控生成并限制数量

来源收集从研究任务和已保存商机生成搜索 query。建议第一版每个商机最多生成 2-4 条 query，覆盖：

- demand: 产品方向 + 目标人群/场景 + 内容平台。
- supply: 产品方向 + 供给来源偏好/批发/起订量。
- competitor: 产品方向 + 同类产品/售价/卖点。
- risk: 产品方向 + 投诉/避坑/质量/售后。

每个任务保存来源数量设置上限，例如 12-20 条，避免搜索成本和结果噪声失控。来源 URL 在同一任务下需要去重，重复来源可以合并为更泛的 `general` 或保留首个关联判断。

Alternative considered: 让 LLM 自由生成不限数量 query。它可能召回更多内容，但成本、延迟和噪声不可控，不适合 MVP 演示。

### 5. Tavily 搜索优先，Extract 作为增强

使用现有 Tavily integration 创建 client。搜索结果中的 `title`、`url`、`content`、`score` 可以直接形成来源候选；对于排名靠前且需要更完整摘要的 URL，再调用 Tavily Extract 获取 `raw_content`。

实现时应把 Tavily 调用封装在 `sources` service 中，便于测试替换。测试环境和本地无凭证时使用确定性 fallback，自动化测试不依赖网络或真实 Tavily API。

Alternative considered: 使用 Playwright 抽取所有页面正文。Playwright 更灵活，但开销高、失败模式多，且登录后抓取不在 MVP 范围。第一版只把 Playwright 保留为未来增强。

### 6. 来源摘要语气保持“线索”而非“证明”

保存的 `summary` 和 `linked_claim` 应使用谨慎表达，例如“可能支持”“可作为初步参考”“仍需验证”。系统不得生成“已证明”“确定有市场”“供给已确认”“竞品已全面核验”等表达。

这既保护用户预期，也让后续 `show-source-transparency` 可以自然展示“公开来源线索”。

### 7. 非阻塞失败策略

来源收集发生错误时，基础商机任务仍可完成。建议策略：

- 如果商机生成或持久化失败，任务仍按现有逻辑进入 `failed`。
- 如果来源收集全部失败，任务保持 `completed`，记录 `collect_research_sources` 阶段事件和应用日志，并在来源 API 返回空列表。
- 如果部分来源成功，保存成功来源，并在事件 metadata 中标记 partial。
- 用户可见文案不展示原始异常堆栈、凭证或内部自增 ID。

Alternative considered: 来源收集失败即任务失败。这样能强制保证结果有来源，但会破坏已完成的 P0 演示闭环，也会让外部搜索服务波动影响核心流程。

## 风险 / 取舍

- [Risk] Tavily 结果与商机判断相关性不足 -> Mitigation: 控制 query 模板、保存 `source_type` 和 `linked_claim`，并在后续分析切片继续筛选和重写。
- [Risk] 来源收集增加任务耗时 -> Mitigation: 限制每个任务 query 和保存来源数量，Extract 只用于少量高分 URL。
- [Risk] 外部搜索失败影响演示 -> Mitigation: 来源收集非阻塞，本地/测试有确定性 fallback，生产失败记录事件和日志。
- [Risk] 用户误解来源为完整调研结论 -> Mitigation: summary、linked_claim 和后续 UI 均使用“公开来源线索”“初步参考”“待验证”语气。
- [Risk] 来源 URL 重复或低质量 -> Mitigation: 同任务下按 URL 去重，保留 score、query 和 raw metadata 供后续调优。
- [Risk] 重新运行后旧来源污染当前结果 -> Mitigation: 重新运行成功保存新商机和新来源时，软删除或默认排除旧来源。
