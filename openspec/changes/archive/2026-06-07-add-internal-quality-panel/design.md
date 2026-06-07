## 背景

当前 MarketPilot 已完成核心研究闭环，并具备三类内部质量能力：

- `research-quality-readiness`：可对已完成任务运行演示就绪检查，并汇总阶段完整性、RAG 索引健康、RAG 检索评测摘要和生成内容 smoke check。
- `generation-quality-evaluation`：可通过内部 runner 对已完成任务运行生成质量评测，并保存 case 级结果与 rubric 摘要。
- `rag-quality-evaluation`：可通过 readiness 或内部 runner 复跑任务内 RAG retriever，并保存 P0 检索指标。

缺口不在研究主链路，而在内部使用体验：演示前需要从任务列表、命令行 runner、readiness API 和日志中拼状态。这个 change 新增一个内部质量面板，把这些状态收束到一个只面向团队的页面中。

## 目标 / 非目标

**目标：**

- 提供内部质量面板页面，支持选择已完成研究任务并查看质量状态。
- 展示最近 readiness run 的整体状态、检查项、关键指标、过期状态和安全错误摘要。
- 支持从面板触发 readiness run 和 generation evaluation run。
- 为 generation evaluation 增加与 readiness 同风格的内部 API，避免前端调用命令行 runner。
- 继续保证普通用户进度页、商机详情、报告页和公开分享页不展示内部质量信息。

**非目标：**

- 不新增登录、角色、权限或真正的访问控制系统。
- 不把内部质量分数变成用户侧商机排序、可信度或市场成立度结论。
- 不重做 RAG 评测集、生成评测集或 readiness runner 的评分逻辑。
- 不新增数据库表；沿用已有 quality evaluation 和 readiness 数据模型。
- 不修改研究任务创建、研究编排、报告分享或公开报告快照契约。

## 技术决策

### 决策 1：新增独立内部页面，通过演示用户菜单进入

面板使用独立前端路由，例如 `/internal/quality`。页面不放入当前“新建研究 / 我的研究”的一级导航，也不从公开分享页、进度页或报告页链接进入；内部团队可从右上角“演示用户”菜单进入。

这样可以在没有完整权限系统的 MVP 阶段降低误触和用户侧暴露风险，同时不改变 `product-skeleton` 对主导航的约束。备选方案是把“演示状态”放回我的研究列表，但这会让普通研究浏览页承担内部运维信息，和现有隐藏边界相冲突。

### 决策 2：复用现有任务与 readiness API，少建聚合层

内部面板的任务列表优先复用现有研究任务读取 API，在前端筛选或展示已完成任务。readiness 触发和最近结果读取复用已有：

- `POST /api/v1/research-tasks/{task_uuid}/readiness-runs`
- `GET /api/v1/research-tasks/{task_uuid}/readiness-runs/latest`

如果实现时发现前端需要分页或服务端筛选，可在同一 change 内给研究任务列表增加保守查询参数；默认行为必须兼容现有调用。

### 决策 3：为生成质量评测补内部 API

当前生成质量评测已有 service、runner、模型和测试，但没有供前端触发的路由。新增与 readiness 命名一致的内部 API：

- `POST /api/v1/research-tasks/{task_uuid}/generation-evaluation-runs`
- `GET /api/v1/research-tasks/{task_uuid}/generation-evaluation-runs/latest`

响应只返回公开 UUID、状态、整体结论、case 计数、rubric 摘要、中文摘要、过期状态和安全错误摘要，不返回完整 prompt、完整网页正文、完整 case 快照、原始异常堆栈或内部自增 ID。

备选方案是让面板只展示 readiness 中纳入的 generation evaluation 摘要，但这会要求使用者先回命令行跑 generation runner，不能解决“面板一站式复查”的核心问题。

### 决策 4：RAG 质量先展示 readiness 摘要，不新增 RAG 评测详情页

面板展示 readiness run 中的 RAG 索引健康和 RAG 检索评测摘要，包括运行 UUID、状态、case 数和 P0 指标。暂不新增 RAG evaluation run 详情页，也不展示每个 evidence 的正文、chunk 原文或完整网页内容。

这保持了本切片的边界：把已有质量信号产品化，而不是扩展评测分析系统。后续如果要排查 case 级检索问题，可以单独开评测详情或评测集扩展 change。

### 决策 5：内部面板不是安全边界

因为项目当前没有认证系统，`/internal/quality` 只能作为产品内的内部工作台约定，不是访问控制。实现应避免从公开页面链接到它，并保证 API 响应不含敏感信息；如果部署到公网环境，需要由部署层或未来 auth change 提供访问保护。

## 风险 / 取舍

- 内部路由没有认证保护 → 在公网演示环境中需要依赖部署层限制访问；本 change 不声称提供权限隔离。
- 面板同时触发 generation evaluation 和 readiness，可能让运行耗时变长 → 操作按钮使用独立 loading / error 状态，失败不影响研究主流程。
- readiness 摘要里的 RAG 信息不够细 → 先展示聚合指标和建议，case 级 RAG 诊断留给后续独立切片。
- 质量信息被误读为用户侧结论 → 页面文案明确标注为内部复查信号，不作为商机成立、利润保证或市场验证结论。
- 新增 generation evaluation API 可能重复 runner 能力 → API 只做薄路由层，复用现有 service，避免双份评分逻辑。

## 迁移计划

- 无数据库迁移；沿用现有 readiness 和 generation evaluation 表。
- 新增前端页面和 API client 后，不影响已有用户路径。
- 新增 generation evaluation 路由后，保留现有 runner，便于命令行和面板两种内部使用方式共存。
- 回滚时可移除内部页面和新增路由；已有 evaluation/readiness 数据不需要迁移或删除。

## 开放问题

- 内部面板是否需要在未来 auth change 后接入角色权限，目前暂不在本 change 内处理。
- 是否需要给研究任务列表增加服务端分页或 `status=completed` 查询参数，取决于实现时现有列表在本地数据量下是否足够。
