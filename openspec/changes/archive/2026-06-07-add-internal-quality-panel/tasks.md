## 1. 后端内部质量 API

- [x] 1.1 新增 generation evaluation API route，支持创建已完成任务的 generation evaluation run。
- [x] 1.2 新增读取最近 generation evaluation run 的 API，默认只返回未软删除记录并标记 stale 状态。
- [x] 1.3 将 generation evaluation route 注册到 v1 router，并复用现有 service、schema 和安全错误摘要逻辑。
- [x] 1.4 补充后端测试，覆盖创建、读取 latest、未完成任务拒绝、未知任务 404、stale 标记和不暴露内部自增 ID / 完整 prompt / 原始异常堆栈。

## 2. 前端 API Client 与类型

- [x] 2.1 在 research API client 中补充 generation evaluation run 类型、创建函数和读取 latest 函数。
- [x] 2.2 确认 readiness client 继续可从内部页面调用，且普通进度页、任务列表和公开分享页不默认读取 readiness。
- [x] 2.3 为内部面板需要的状态标签、日期展示和安全错误展示补充轻量工具或局部映射，不新增运行时依赖。

## 3. 内部质量面板页面

- [x] 3.1 新增 `/internal/quality` 页面，展示中文内部质量复查界面和谨慎边界说明。
- [x] 3.2 实现研究任务选择区，展示未软删除任务的公开 UUID、标题、状态、阶段和时间，并突出已完成任务可复查。
- [x] 3.3 实现 readiness 摘要区，展示整体状态、运行状态、stale、检查项、聚合指标、建议动作和安全错误摘要。
- [x] 3.4 实现 generation evaluation 摘要区，展示整体状态、case 计数、rubric 维度摘要、stale、中文摘要和安全错误摘要。
- [x] 3.5 实现 RAG 质量摘要区，从 readiness 检查项中展示索引健康、评测运行 UUID、case 计数和 P0 检索指标。
- [x] 3.6 实现运行 readiness 和 generation evaluation 的操作按钮，包含独立 loading、成功刷新和失败提示。
- [x] 3.7 处理空任务、无已完成任务、无 readiness run、无 generation evaluation run、API 连接失败和任务未完成等状态。

## 4. 用户侧隐藏边界

- [x] 4.1 在演示用户菜单新增内部质量复查入口，并确认一级产品导航不新增内部质量面板入口。
- [x] 4.2 确认研究进度页、商机详情页、报告页和公开分享页不展示内部质量面板入口、评测分数、readiness 检查项或内部错误摘要。
- [x] 4.3 更新前端 UI contract 测试，覆盖内部面板存在且用户侧页面继续隐藏内部质量信息。

## 5. 验证与演示检查

- [x] 5.1 运行 `openspec validate add-internal-quality-panel --strict` 并修正规格问题。
- [x] 5.2 运行后端测试，确认新增 API 和既有质量能力不回退。
- [x] 5.3 运行前端测试和 typecheck，确认内部页面、API client 和隐藏边界通过。
- [x] 5.4 本地打开内部质量面板，验证已完成任务的 readiness、generation evaluation 和 RAG 摘要能读取、运行和刷新。
- [x] 5.5 检查日志或 trace metadata，确认质量运行记录不包含 API key、完整 prompt、完整网页正文、RAG chunk 原文、内部自增 ID 或原始异常堆栈。
