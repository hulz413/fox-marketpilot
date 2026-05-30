## 背景

MarketPilot 已经完成项目骨架、产品骨架和真实研究任务创建。当前用户可以提交自然语言需求并看到 `research_tasks` 记录，但任务状态停留在 `created/intake`，不会调用 Agent、LLM、Celery 或 LangGraph，也不会生成可供商机排行、详情和报告使用的真实结果。

Roadmap 将 `run-opportunity-research` 定义为 P0 的下一块核心切片：用户提交需求后，系统能完成一次基础商机研究，并生成 3-5 个包含名称、产品方向、目标人群、推荐理由、渠道、价格带、粗略利润、风险等级和下一步建议的商机结果。本 change 需要连接后端任务生命周期、轻量 Agent/LLM 生成、结果持久化和前端读取，但不进入 P1 的来源、RAG、竞品、利润、风险和行动计划深挖。

## 目标 / 非目标

**目标：**

- 允许用户对已创建的研究任务启动一次基础商机研究。
- 将研究任务从 `created` 推进到 `queued`、`running`、`completed` 或 `failed`。
- 使用 LangGraph 实现一个单图 Agent：归一化输入、生成商机、校验结果、持久化结果。
- 通过 OpenAI-compatible LLM provider 生成 3-5 个结构化商机结果。
- 明确基础商机结果是无外部前置调研的待验证推荐草案，避免产品文案暗示来源支撑。
- 在本地或测试缺少 LLM key 时提供确定性 fallback，保证开发和 CI 可验证。
- 新增商机结果持久化和读取 API，让排行榜、详情页和基础报告入口读取真实后端数据。
- 记录基础运行日志、运行 ID、当前阶段和失败原因，为后续 `show-research-progress` 与 `observe-agent-runs` 留出锚点。

**非目标：**

- 不实现多 Agent 分工、复杂意图路由或开放域聊天。
- 不做外部前置调研，不调用搜索、抓取、提取或检索工具。
- 不调用 Tavily、Playwright、RAG、向量检索或网页正文提取。
- 不保存公开来源、引用依据、竞品参考、货源候选、详细利润模型或完整风险复核。
- 不要求 LangSmith trace 完整接入；本 change 只保留 nullable `trace_id` 和基础日志。
- 不实现 SSE 实时进度页；后续 `show-research-progress` 读取本 change 产生的状态字段即可。
- 不实现完整最终报告模型；报告页可先基于商机结果做基础汇总。

## 技术决策

### 决策：使用 LangGraph 单图工作流，而不是多 Agent

本 change 使用 LangGraph 实现单图工作流，内部节点保持线性：

```text
normalize_intake
  -> generate_opportunities
  -> validate_results
  -> persist_results
```

`build_research_graph()` 应返回真实可执行图，而不是当前占位异常。`normalize_intake` 将任务的自然语言需求和结构化字段合并成统一研究上下文，并补上默认演示约束，例如中文输出、国内供给市场、小预算验证和不自动交易。它只做轻量需求归一化，不做复杂意图分类，因为用户入口已经限定为“商机研究”。

`generate_opportunities` 调用配置中的 OpenAI-compatible LLM provider，要求返回 3-5 个 JSON 商机。`validate_results` 使用 Pydantic schema 校验数量、必填字段、排序、风险等级和文本长度。`persist_results` 负责在事务中替换或写入当前任务的商机结果，并更新任务状态。Celery task 负责装载任务上下文并调用该 LangGraph 图；节点内部仍可使用可注入的 LLM 生成器和 deterministic fallback，方便测试。

备选方案：

- 不用 LangGraph、只写普通 service：代码更少，但会偏离既定技术栈，也会削弱后续 `observe-agent-runs` 接入 LangSmith trace 的自然路径。
- 多 Agent：DemandAgent、SupplyAgent、CompetitorAgent、RiskAgent 等更贴近长期目标，但 P0 缺少真实来源和工具支撑，提前拆分会增加协调、合并和失败恢复复杂度。
- 纯规则生成：稳定但不能体现商机顾问 Agent 的核心价值，也难以从自定义输入中生成有变化的推荐。
- 创建任务时自动研究：链路更短，但会让提交动作和执行动作耦合，也不利于失败重试和后续进度页表达。

### 决策：本切片不做外部前置调研

本 change 的 `generate_opportunities` 节点直接基于研究任务输入、结构化条件、产品默认演示场景和模型已有知识生成基础商机。它不调用 Tavily、Playwright、网页提取、RAG、pgvector 或其他外部检索工具，也不创建来源记录。生成结果应被视为“基础推荐”“待验证商机”或“验证草案”，不能在 UI、报告或 API 文案中表达为“已完成市场调研”“有公开来源支撑”或“已核验竞品/供给”。

这样做的目的是让 P0 先跑通任务到结果的闭环，把可信度增强留给后续 `collect-research-sources`、`show-source-transparency`、`suggest-supply-candidates` 和 `compare-competitor-references` 等切片。

备选方案：

- 在本 change 内加入轻量搜索：可信度会更好，但会提前引入来源存储、失败重试、搜索配额、提取质量和引用展示问题，与后续来源透明度切片重叠。
- 先做来源收集再做商机生成：更像完整研究流程，但会推迟排行榜、详情页和基础报告的真实数据接入。

### 决策：通过显式 run endpoint 启动研究

新增 API 建议为：

- `POST /api/v1/research-tasks/{task_uuid}/runs`

该 endpoint 校验任务存在且未软删除，若任务未在运行中则生成 `run_id`，将状态设为 `queued`，清空上一轮失败原因，并投递 Celery 任务。Celery worker 开始执行时设置 `running`，完成后设置 `completed`，失败时设置 `failed` 并保存中文可读失败摘要。

如果同一任务已经是 `queued` 或 `running`，重复启动请求 SHALL 返回当前任务状态，不重复投递新的运行。若任务已经 `completed`，本 change 可以允许重新运行：重新运行会清理或替换旧商机结果，并生成新的 `run_id`。这样为历史任务 rerun 留下自然入口。

备选方案：

- 创建任务后立即自动投递：更少点击，但与现有 `create-research-task` 规格中“创建任务不执行 Agent”的边界冲突。
- 只提供同步 `POST /run-and-wait`：开发简单，但研究执行时间不可控，也不符合技术栈中 Celery + Redis 的异步任务方向。

### 决策：新增 `opportunities` 结果表

新增 `opportunities` 表作为基础商机结果表。它遵循数据库通用字段规范：

- `id`: 数据库内部自增主键
- `uuid`: 对外公开 UUID，用于 API、前端路由和跨模块引用
- `research_task_id`: 内部外键，关联 `research_tasks.id`
- `rank`: 推荐排序，正整数
- `name`: 商机名称
- `product_direction`: 产品方向
- `target_audience`: 目标人群
- `recommendation_reason`: 推荐理由
- `suitable_channels`: JSON string list，适合渠道
- `price_band`: 价格带
- `rough_margin`: 粗略利润空间
- `risk_level`: `low`、`medium` 或 `high`
- `priority_label`: 推荐优先级文案
- `next_step_summary`: 下一步建议摘要
- `created_at` / `updated_at`: 创建和更新时间戳
- `deleted_at`: 软删除时间戳，默认空

读取商机结果时默认只返回 `deleted_at IS NULL` 的记录，按 `rank` 升序排序。重新运行任务时，可以软删除该任务旧商机并写入新结果，避免历史数据硬删除造成审计困难。

备选方案：

- 把商机结果放到 `research_tasks.result_json`：实现快，但排行榜、详情页、后续来源/报告关联都会缺少稳定 opportunity UUID。
- 直接建立 report 表：报告是后续切片，本 change 只需要让基础报告视图能从商机结果汇总。

### 决策：LLM 输出使用严格结构化 schema，并提供确定性 fallback

LLM prompt 明确要求中文输出、国内商机演示语境、小成本验证边界，以及 3-5 个符合 schema 的 JSON 商机。后端不信任模型原始输出，必须解析并通过 Pydantic 校验后才能落库。校验失败可以重试一次；仍失败则任务进入 `failed`。

当 `ENVIRONMENT` 为 local/test 且 `LLM_API_KEY` 为空时，系统使用 `DeterministicDemoEngine` 基于输入字段生成稳定的 3 个中文商机。生产环境缺少 LLM key 时应失败并记录配置错误，而不是静默生成 fallback 结果。

备选方案：

- 只依赖 prompt 约束，不做 schema 校验：实现简单，但容易把缺字段或格式错误结果写入数据库。
- 在所有环境都 fallback：演示更稳，但会掩盖生产 LLM 配置问题。

### 决策：前端从任务结果 API 读取真实数据，保留 demo 空状态

商机推荐页和详情页应从后端读取真实 opportunities。推荐的 API 形态：

- `GET /api/v1/research-tasks/{task_uuid}/opportunities`
- `GET /api/v1/opportunities/{opportunity_uuid}`

任务列表中的操作入口可根据状态显示“开始研究”“查看商机”或“重新运行”。当任务尚未完成或没有结果时，前端展示中文状态说明和返回任务列表/新建研究入口。静态 demo 数据可以保留为空状态或无后端连接时的产品骨架参考，但不再作为已完成任务的真实数据来源。

备选方案：

- 继续使用 `/opportunities` 全局 demo 列表：不需要路由改动，但无法表达某一次研究任务对应的结果。
- 一次性完成报告页真实模型：范围过大，应该留给 `generate-final-report`。

## 风险 / 取舍

- [Risk] LLM 输出不稳定或不符合 schema -> Mitigation: 使用结构化 schema 校验、一次重试、失败状态和确定性 fallback 覆盖测试路径。
- [Risk] Celery worker 未启动导致任务停在 `queued` -> Mitigation: 本地启动脚本已启动 Celery；前端展示 queued/running 状态，后续进度切片再补轮询/SSE。
- [Risk] 重新运行会让旧商机链接失效 -> Mitigation: 旧结果软删除，新结果使用新 UUID；前端从任务入口进入最新结果。
- [Risk] 基础商机结果缺少来源依据，用户信任度有限 -> Mitigation: 明确本 change 不声称来源透明，后续 `collect-research-sources` 和 `show-source-transparency` 补强。
- [Risk] UI 文案让用户误以为结果已经过公开调研 -> Mitigation: 将结果命名为基础推荐或待验证商机，避免出现“已调研”“来源依据”“竞品核验”等超出本切片能力的表达。
- [Risk] 本 change 触达前后端、worker、数据库、LangGraph 和 LLM，测试面较宽 -> Mitigation: 将 LangGraph 节点依赖抽象为可注入组件，用 deterministic generator 覆盖单元/集成测试。

## 迁移计划

1. 扩展 `research_tasks` status/stage 枚举和服务方法，保留创建后仍为 `created/intake` 的现有行为。
2. 新增 `opportunities` SQLAlchemy model 和 Alembic migration，包含内部 `id`、公开 `uuid`、标准时间戳、`deleted_at`、任务外键和排序索引。
3. 新增 opportunity result schemas、repository、service 和 FastAPI routes。
4. 新增 research run service、Celery task 和 LangGraph 单图 Agent。
5. 新增 LLM schema 校验和 deterministic fallback。
6. 更新前端任务列表、商机推荐页、详情页和基础报告入口读取真实任务结果。
7. 增加后端和前端测试，覆盖成功、失败、重复启动、重新运行和无结果状态。

Rollback 时可以停止调用 run endpoint，回退前端到任务列表入口，并回滚 `opportunities` migration。`research_tasks` 新增状态值不会破坏已有 `created` 任务。

## 开放问题

- 前端新建任务成功后是否立即自动调用 run endpoint，还是让用户在任务列表点击“开始研究”？建议本 change 先在创建成功后自动启动，以满足最短演示闭环，同时任务列表保留手动开始/重试入口。
- 是否在本 change 中为报告页新增 `/reports/{task_uuid}` 的真实路由？建议只做基础汇总读取，不新增独立 report 表。
