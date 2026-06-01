## 背景

当前系统已经具备完整研究任务闭环、阶段事件、来源收集、任务内 RAG evidence chunks、RAG 检索评测、增强分析和报告分享能力。缺口不在用户侧结果展示，而在演示前缺少一个统一的内部检查结果：团队需要快速知道某条完成任务是否可演示、哪些增强节点缺失、RAG 索引是否健康、生成内容是否仍保持“初步参考/待验证”的边界。

本 change 新增 `research-quality-readiness` 能力。它读取现有研究任务和结果，不改变研究主流程，不把内部质量分数暴露成用户侧商机可信度。

## 目标 / 非目标

**目标：**

- 为已完成研究任务生成可持久化的质量就绪检查运行，输出整体状态、检查项状态、摘要指标和可操作原因。
- 覆盖阶段完整性、RAG 索引健康、RAG 检索评测摘要、生成内容 smoke check 和报告分享快照检查。
- 在任务进度页展示内部「演示就绪检查」面板，并可选在研究历史列表展示轻量状态标识。
- 保持安全边界：不暴露内部自增 ID、完整网页正文、chunk 原文、原始异常堆栈、API key 或内部 trace 细节。
- 确保 readiness 检查失败不影响用户创建任务、运行研究、查看结果、生成分享或撤销分享。

**非目标：**

- 不重写基础商机生成、增强分析生成或 RAG retriever 排序逻辑。
- 不引入外部前置深度调研、多 Agent 协作、真实平台抓取或人工标注后台。
- 不把 readiness 状态作为推荐排序、商机评分、市场成立度或用户可见可信度依据。
- 不在公开分享页展示 readiness、RAG 评测、trace、内部错误或调试信息。

## 技术决策

### 1. 新增单表保存 readiness run 和检查明细 JSON

新增 `research_quality_readiness_runs` 表，用一条记录保存一次检查运行：

- `id`：数据库内部自增 ID，仅内部关联使用。
- `uuid`：对外读取使用的公开 UUID。
- `research_task_id`：关联研究任务内部 ID。
- `research_run_id`：检查时任务的当前 `run_id`，用于判断结果是否过期。
- `status`：检查运行状态，例如 `running`、`completed`、`partial`、`failed`。
- `overall_status`：就绪结论，例如 `ready`、`warning`、`failed`。
- `summary`：中文安全摘要。
- `checks`：检查项数组 JSON，保存 `key`、`label`、`status`、`severity`、`summary`、`metrics`、`reasons` 和 `actions`。
- `metrics`：整体汇总 JSON，例如机会数、来源数、chunk 数、完成检查数、warning 数、failed 数。
- `rag_evaluation_run_uuid`：可空，关联最近或本次 RAG 检索评测运行的公开 UUID。
- `trace_id`、`trace_url`：可空，用于内部观测。
- `started_at`、`completed_at`、`error_summary`。
- 通用字段：`created_at`、`updated_at`、`deleted_at`。

选择单表 + JSON 明细，是因为第一版检查项数量固定且偏内部观察；相比拆多张明细表，能减少迁移和查询复杂度。后续如果需要按检查项维度做趋势分析，再拆出 detail 表。

备选方案是完全不落库、每次实时计算。该方案实现更轻，但历史页 badge、结果过期判断、演示前复查记录和失败追踪都会变弱，因此不采用。

### 2. readiness runner 同步读取现有结果，不接入研究主图

新增后端模块 `research_quality_readiness`，提供 service/repository/schema/runner/API。readiness runner 默认同步执行，只读取现有持久化结果和可选触发 RAG 检索评测，不加入 `backend/app/agents/graph.py` 的研究主流程。

检查项建议固定为：

- `stage_completeness`：读取当前 run 的阶段事件，检查关键阶段是否完成、失败或缺失。
- `rag_index_health`：读取任务来源、active RAG chunks、embedding 状态和索引阶段 metadata。
- `rag_retrieval_evaluation`：复用现有 RAG 检索评测，保存或读取评测摘要。
- `generation_content_smoke`：读取商机和增强分析，检查关键字段完整性、空结果和谨慎边界表达。
- `report_share_snapshot`：检查是否存在 active share 和快照；缺失只给 warning 或 unchecked，不阻断 readiness。

整体状态聚合规则保持保守：

- 任一关键检查为 `failed` 时整体为 `failed`。
- 无 failed 但存在 warning/skipped/stale 时整体为 `warning`。
- 所有关键检查通过且结果未过期时整体为 `ready`。

任务未完成时不生成 `ready` 结论，API 返回中文错误或创建 `failed` readiness run，避免把未完成任务误标为可演示。

### 3. 复用 RAG 检索评测，但不把分数包装成商机结论

readiness runner 可以调用现有 `rag_quality_evaluation` 服务运行默认中文评测集，也可以读取最近一次同任务评测结果。第一版优先选择“运行时可配置”：

- 默认在有 active chunks 时运行一次 RAG 检索评测并保存摘要。
- 当缺少 chunks 或评测服务失败时，readiness run 记录 warning/failed check，但不修改研究任务状态。
- 摘要只包含 run UUID、状态、case 数、平均 P0 指标和安全错误摘要。

前端只展示面向内部用户的概览，例如 `hit_rate@k`、`mrr@k` 和 case 状态；不展示完整 chunk 文本，不在报告或公开分享页展示评测分数。

### 4. 生成内容 smoke check 使用规则检查，不做 LLM-as-judge

第一版生成内容检查采用确定性规则：

- 检查每个 active opportunity 是否具备对应的需求洞察、货源候选、竞品参考、验证预算、风险复核和行动计划记录。
- 检查关键字段是否为空、数组是否为空、数量是否明显不足。
- 检查用户可见文本是否包含谨慎表达，例如“初步”“待验证”“候选”“参考”“需要确认”等。
- 检查高风险断言，例如“已核验”“已确认库存”“保证利润”“自动联系供应商”“已经完成真实验证”等；命中时标记 warning 或 failed。

暂不使用 LLM-as-judge，避免引入新的模型调用成本、不可重复性和提示调优负担。后续如果需要更强质量评测，可以单独提出生成层评测 change。

### 5. 前端只在应用内展示内部 readiness，不进入公开分享页

前端新增读取和运行 readiness 的 API client。任务进度页在任务完成后展示「演示就绪检查」面板：

- 未检查：展示运行检查按钮。
- running：展示检查中状态。
- ready/warning/failed：展示整体状态、最近检查时间、检查项摘要和查看原因。
- 结果过期：当 readiness 的 `research_run_id` 与任务当前 `run_id` 不一致时提示重新检查。

研究历史列表可选展示轻量 badge：`可演示`、`需复查`、`未检查`、`已过期`。公开分享页不调用 readiness API，不展示 readiness 数据。

## 迁移计划

1. 新增 Alembic migration 创建 `research_quality_readiness_runs` 表和必要索引。
2. 新增后端模块和内部 API，不接入研究主流程。
3. 新增前端 API client、进度页面板和历史页 badge。
4. 添加后端单元测试、前端契约测试和必要的 OpenSpec 校验。

回滚时可以隐藏前端面板并移除 API router；已创建的 readiness run 保留为内部历史数据，或通过软删除统一排除读取。

## 风险 / 取舍

- [Risk] readiness 被误解为用户侧可信度评分 → Mitigation: 文案固定为内部演示就绪检查，不出现在公开分享页，不影响推荐排序。
- [Risk] RAG 检索评测耗时影响 API 响应 → Mitigation: 第一版固定小评测集，失败时记录 warning；如后续变慢再切到 Celery。
- [Risk] 规则化 smoke check 漏掉语义质量问题 → Mitigation: 第一版只承诺结构完整性和边界文案检查，生成质量深评估后续单独切片。
- [Risk] 任务重新运行后 readiness 结果陈旧 → Mitigation: 保存 `research_run_id` 并在读取时标记 stale。
- [Risk] 检查项读取软删除数据造成误判 → Mitigation: 所有关联数据默认只读取 `deleted_at` 为空的 active 记录。

## 开放问题

- 是否需要通过环境变量隐藏 readiness 面板，只在内部演示环境显示？第一版建议不加复杂权限，仅确保公开分享页不展示。
- RAG 检索评测是否每次 readiness run 都重新执行，还是优先复用最近一次同 run 评测？第一版可实现为默认重新执行，并保留后续优化空间。
